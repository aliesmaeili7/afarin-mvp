"use client";

import type { AssetRenderSpec, TextLayer } from "@/types/domain";
import { AdCanvas } from "@/features/campaign/ad-renderer/AdCanvas";
import { EDITOR_CHROME_ATTR } from "@/features/campaign/ad-renderer/textLayers";
import { cn } from "@/components/ui/cn";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import { useLayerGestures } from "./useLayerGestures";

export function EditorStage({
  spec,
  width,
  height,
  layers,
  selectedId,
  onSelect,
  onLiveChange,
  onCommit,
  showSafeArea = false,
  dir = "rtl",
  scrim = true,
}: {
  spec: AssetRenderSpec;
  width: number;
  height: number;
  layers: TextLayer[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  onLiveChange: (layers: TextLayer[]) => void;
  onCommit: (layers: TextLayer[]) => void;
  /** Story crop guides. Off for square formats, which have no crop. */
  showSafeArea?: boolean;
  dir?: "rtl" | "ltr";
  scrim?: boolean;
}) {
  const { t } = useI18n();
  const gestures = useLayerGestures({
    layers,
    selectedId,
    onSelect,
    onLiveChange,
    onCommit,
  });

  return (
    <div
      data-editor-stage
      className="relative mx-auto w-full max-w-sm touch-none overflow-hidden rounded-2xl shadow-lift"
      style={{ touchAction: gestures.touchAction }}
      onPointerDown={gestures.onStagePointerDown}
      onPointerMove={gestures.onPointerMove}
      onPointerUp={gestures.onPointerUp}
      onPointerCancel={gestures.onPointerUp}
      onTouchStart={gestures.onTouchStart}
      onTouchMove={gestures.onTouchMove}
      onTouchEnd={gestures.onTouchEnd}
    >
      <AdCanvas
        spec={spec}
        width={width}
        height={height}
        mode="view"
        dir={dir}
        scrim={scrim}
      />

      <div className="absolute inset-0" {...{ [EDITOR_CHROME_ATTR]: "" }}>
        {showSafeArea ? <SafeAreaGuides /> : null}
        {layers.map((layer) => {
          const selected = layer.id === selectedId;
          return (
            <button
              key={layer.id}
              type="button"
              data-layer-hit={layer.id}
              aria-label={t("editor.selectLayer")}
              className={cn(
                "absolute min-h-11 cursor-grab touch-none rounded-md border-2 bg-transparent p-0",
                selected
                  ? "border-white shadow-[0_0_0_1px_rgba(124,58,237,0.9)]"
                  : "border-transparent",
              )}
              style={{
                left: `${layer.x * 100}%`,
                top: `${layer.y * 100}%`,
                width: `${layer.width * 100}%`,
                height: "auto",
                minHeight: "2.75rem",
              }}
              onPointerDown={(event) => gestures.onPointerDown(event, layer.id, "move")}
            />
          );
        })}
        {selectedId
          ? layers
              .filter((layer) => layer.id === selectedId)
              .map((layer) => (
                <button
                  key={`resize-${layer.id}`}
                  type="button"
                  data-layer-hit={layer.id}
                  aria-label={t("editor.resizeLayer")}
                  className="absolute z-10 size-11 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-brand-600 shadow-soft"
                  style={{
                    left: `${(layer.x + layer.width) * 100}%`,
                    top: `${(layer.y + Math.min(0.12, layer.font_size * 2.2)) * 100}%`,
                  }}
                  onPointerDown={(event) =>
                    gestures.onPointerDown(event, layer.id, "resize")
                  }
                />
              ))
          : null}
      </div>
    </div>
  );
}

function SafeAreaGuides() {
  const { t } = useI18n();
  return (
    <>
      <div
        className="pointer-events-none absolute inset-x-0 top-0 bg-black/25"
        style={{ height: "14%" }}
      />
      <div
        className="pointer-events-none absolute inset-x-0 bottom-0 bg-black/30"
        style={{ height: "18%" }}
      />
      <p className="pointer-events-none absolute inset-x-0 top-[2%] text-center text-[10px] font-semibold text-white/80">
        {t("editor.safeArea")}
      </p>
    </>
  );
}
