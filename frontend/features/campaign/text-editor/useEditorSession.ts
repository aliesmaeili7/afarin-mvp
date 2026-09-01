"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { RewriteIntent } from "@/lib/api/types";
import type { AssetRenderSpec, CampaignAsset, TextLayer } from "@/types/domain";
import { useDisplayError, useI18n } from "@/lib/i18n/PreferencesProvider";
import {
  applyRoleText,
  clampLayer,
  defaultTextLayers,
  hydrateEditorLayers,
  MAX_TEXT_LAYERS,
  newCustomLayer,
  specWithLayers,
  syncContentFieldsFromLayers,
} from "@/features/campaign/ad-renderer/textLayers";
import { useToast } from "@/components/ui/Toast";
import {
  canRedo,
  canUndo,
  cloneLayers,
  createHistory,
  pushHistory,
  redoHistory,
  sameSnapshot,
  undoHistory,
  type HistoryState,
} from "./editorHistory";

export type SaveStatus = "idle" | "saving" | "saved" | "error";

const SAVE_DELAY_MS = 700;

function initialLayers(spec: AssetRenderSpec): TextLayer[] {
  return hydrateEditorLayers(spec);
}

/**
 * What the editor needs to know about an advertising asset.
 *
 * Persistence sits behind a callback so the same editor can save different
 * campaign assets. Educational posts do not use this editor.
 */
export interface EditorTarget {
  spec: AssetRenderSpec;
  /** Null restores the generated layout. */
  save(layers: TextLayer[] | null): Promise<void>;
  /** Absent when the content type has no AI copy rewrite. */
  rewrite?(intent: RewriteIntent): Promise<AssetRenderSpec>;
}

export function campaignEditorTarget(
  asset: CampaignAsset,
  campaignId: string,
): EditorTarget {
  return {
    spec: asset.metadata_json as AssetRenderSpec,
    async save(layers) {
      await api.updateAssetText(campaignId, asset.id, { text_layers: layers });
    },
    async rewrite(intent) {
      const updated = await api.rewriteAssetText(campaignId, asset.id, intent);
      return updated.metadata_json as AssetRenderSpec;
    },
  };
}

export function useEditorSession(target: EditorTarget) {
  const { toast } = useToast();
  const { t } = useI18n();
  const displayError = useDisplayError();
  const { spec } = target;
  const saveLayers = target.save;
  const rewriteText = target.rewrite;
  const [layers, setLayers] = useState<TextLayer[]>(() => initialLayers(spec));
  const [selectedId, setSelectedId] = useState<string | null>(
    () => initialLayers(spec)[0]?.id ?? null,
  );
  const [history, setHistory] = useState<HistoryState<TextLayer[]>>(() =>
    createHistory(cloneLayers(initialLayers(spec))),
  );
  const [status, setStatus] = useState<SaveStatus>("idle");
  const [mutated, setMutated] = useState(false);
  const [rewriting, setRewriting] = useState(false);

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const layersRef = useRef(layers);
  const mutatedRef = useRef(false);

  useEffect(() => {
    layersRef.current = layers;
  }, [layers]);

  const selected = layers.find((layer) => layer.id === selectedId) ?? null;

  const previewSpec = useMemo(
    () => specWithLayers(spec, layers),
    [spec, layers],
  );

  const persist = useCallback(
    async (next: TextLayer[] | null) => {
      setStatus("saving");
      try {
        await saveLayers(next);
        setStatus("saved");
      } catch (caught) {
        setStatus("error");
        toast(displayError(caught), "error");
      }
    },
    [saveLayers, toast, displayError],
  );

  const scheduleSave = useCallback(
    (next: TextLayer[]) => {
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => {
        void persist(next);
      }, SAVE_DELAY_MS);
    },
    [persist],
  );

  const apply = useCallback(
    (next: TextLayer[], { commitHistory = true, save = true } = {}) => {
      const clamped = next.map(clampLayer);
      setLayers(clamped);
      layersRef.current = clamped;
      if (commitHistory) {
        setHistory((current) => pushHistory(current, cloneLayers(clamped)));
      }
      if (save) {
        mutatedRef.current = true;
        setMutated(true);
        scheduleSave(clamped);
      }
    },
    [scheduleSave],
  );

  const liveChange = useCallback((next: TextLayer[]) => {
    const clamped = next.map(clampLayer);
    setLayers(clamped);
    layersRef.current = clamped;
  }, []);

  const commit = useCallback(
    (next: TextLayer[] = layersRef.current) => {
      apply(next, { commitHistory: true, save: true });
    },
    [apply],
  );

  const patchSelectedLive = useCallback(
    (patch: Partial<TextLayer>) => {
      if (!selectedId) return;
      const next = layersRef.current.map((layer) =>
        layer.id === selectedId ? clampLayer({ ...layer, ...patch }) : layer,
      );
      liveChange(next);
      mutatedRef.current = true;
      setMutated(true);
      scheduleSave(next);
    },
    [liveChange, scheduleSave, selectedId],
  );

  const updateSelected = useCallback(
    (patch: Partial<TextLayer>) => {
      if (!selectedId) return;
      const next = layersRef.current.map((layer) =>
        layer.id === selectedId ? clampLayer({ ...layer, ...patch }) : layer,
      );
      commit(next);
    },
    [commit, selectedId],
  );

  const addLayer = useCallback(() => {
    if (layersRef.current.length >= MAX_TEXT_LAYERS) {
      toast(t("errors.textLayersLimit"), "error");
      return;
    }
    const created = newCustomLayer(spec);
    const next = [...layersRef.current, created];
    setSelectedId(created.id);
    commit(next);
  }, [commit, spec, toast, t]);

  const deleteSelected = useCallback(() => {
    if (!selectedId || layersRef.current.length <= 1) return;
    const next = layersRef.current.filter((layer) => layer.id !== selectedId);
    setSelectedId(next[0]?.id ?? null);
    commit(next);
  }, [commit, selectedId]);

  const resetLayout = useCallback(() => {
    const defaults = defaultTextLayers(spec);
    setSelectedId(defaults[0]?.id ?? null);
    setLayers(defaults);
    layersRef.current = defaults;
    setHistory(createHistory(cloneLayers(defaults)));
    mutatedRef.current = true;
    setMutated(true);
    void persist(null);
  }, [persist, spec]);

  const undo = useCallback(() => {
    setHistory((current) => {
      const next = undoHistory(current);
      if (sameSnapshot(next, current)) return current;
      setLayers(cloneLayers(next.present));
      layersRef.current = next.present;
      mutatedRef.current = true;
      setMutated(true);
      scheduleSave(next.present);
      return next;
    });
  }, [scheduleSave]);

  const redo = useCallback(() => {
    setHistory((current) => {
      const next = redoHistory(current);
      if (sameSnapshot(next, current)) return current;
      setLayers(cloneLayers(next.present));
      layersRef.current = next.present;
      mutatedRef.current = true;
      setMutated(true);
      scheduleSave(next.present);
      return next;
    });
  }, [scheduleSave]);

  const rewrite = useCallback(
    async (intent: RewriteIntent) => {
      if (!rewriteText) return;
      setRewriting(true);
      try {
        if (timerRef.current) {
          clearTimeout(timerRef.current);
          await persist(layersRef.current);
        }
        const nextSpec = await rewriteText(intent);
        const role = intent === "new_headline" ? "headline" : "cta";
        const text =
          role === "headline" ? nextSpec.headline_fa : (nextSpec.cta_fa ?? "");
        const withRole = applyRoleText(layersRef.current, role, text);
        const synced = Array.isArray(nextSpec.text_layers)
          ? nextSpec.text_layers
          : withRole;
        setLayers(synced);
        layersRef.current = synced;
        setHistory((current) => pushHistory(current, cloneLayers(synced)));
        mutatedRef.current = true;
        setMutated(true);
        toast(t("result.textReady"));
      } catch (caught) {
        toast(displayError(caught), "error");
      } finally {
        setRewriting(false);
      }
    },
    [rewriteText, persist, toast, t, displayError],
  );

  const flush = useCallback(async () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    if (!mutatedRef.current) return;
    await persist(layersRef.current);
  }, [persist]);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const meta = event.metaKey || event.ctrlKey;
      if (meta && event.key.toLowerCase() === "z") {
        event.preventDefault();
        if (event.shiftKey) redo();
        else undo();
      }
      if (event.key === "Escape") setSelectedId(null);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [redo, undo]);

  return {
    spec,
    layers,
    previewSpec: syncContentFieldsFromLayers(previewSpec, layers),
    selected,
    selectedId,
    setSelectedId,
    status,
    mutated,
    rewriting,
    canUndo: canUndo(history),
    canRedo: canRedo(history),
    liveChange,
    commit,
    patchSelectedLive,
    updateSelected,
    addLayer,
    deleteSelected,
    resetLayout,
    undo,
    redo,
    rewrite,
    canRewrite: rewriteText !== undefined,
    flush,
  };
}
