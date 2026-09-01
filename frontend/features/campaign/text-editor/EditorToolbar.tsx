"use client";

import type { TextLayer, TextLayerAlign, TextLayerBackground } from "@/types/domain";
import { AD_FONTS } from "@/features/campaign/ad-renderer/fonts";
import { Button } from "@/components/ui/Button";
import { cn } from "@/components/ui/cn";
import { ASSET_REWRITE_CHIPS, RewriteChips } from "@/features/campaign/result/RewriteChips";
import type { RewriteIntent } from "@/lib/api/types";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import type { TranslationKey } from "@/lib/i18n/t";

type TabId = "text" | "style" | "color" | "align";

const TAB_KEYS: { id: TabId; key: TranslationKey }[] = [
  { id: "text", key: "editor.tabText" },
  { id: "style", key: "editor.tabStyle" },
  { id: "color", key: "editor.tabColor" },
  { id: "align", key: "editor.tabAlign" },
];

const SWATCHES = ["#ffffff", "#17121f", "#e9b44c", "#7c3aed", "#fb7263", "#2fb98a"];

export function EditorToolbar({
  tab,
  onTab,
  selected,
  canDelete,
  rewriting,
  onLiveChange,
  onCommitChange,
  onCommit,
  onDelete,
  onRewrite,
  canRewrite = true,
}: {
  tab: TabId;
  onTab: (tab: TabId) => void;
  selected: TextLayer | null;
  canDelete: boolean;
  rewriting: boolean;
  onLiveChange: (patch: Partial<TextLayer>) => void;
  onCommitChange: (patch: Partial<TextLayer>) => void;
  onCommit: () => void;
  onDelete: () => void;
  onRewrite: (intent: RewriteIntent) => void;
  /** Off for content types with no AI copy rewrite, such as educational posts. */
  canRewrite?: boolean;
}) {
  const { t } = useI18n();
  return (
    <div className="border-t border-border bg-surface pb-safe">
      <div className="flex gap-1 overflow-x-auto px-3 pt-2">
        {TAB_KEYS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onTab(item.id)}
            className={cn(
              "h-10 shrink-0 rounded-full px-3 text-sm font-semibold",
              tab === item.id
                ? "bg-ink-900 text-white"
                : "bg-ink-50 text-ink-600",
            )}
          >
            {t(item.key)}
          </button>
        ))}
      </div>

      <div className="max-h-[40dvh] overflow-y-auto p-4">
        {!selected ? (
          <p className="text-sm text-muted">{t("editor.selectHint")}</p>
        ) : (
          <>
            {tab === "text" ? (
              <div className="flex flex-col gap-3">
                <textarea
                  rows={3}
                  value={selected.text}
                  onChange={(event) => onLiveChange({ text: event.target.value })}
                  onBlur={onCommit}
                  className="w-full rounded-2xl border border-ink-200 px-3 py-2 text-sm leading-7"
                />
                {canRewrite ? (
                  <RewriteChips
                    chips={ASSET_REWRITE_CHIPS}
                    onSelect={onRewrite}
                    disabled={rewriting}
                  />
                ) : null}
                {canDelete ? (
                  <Button variant="outline" onClick={onDelete}>
                    {t("editor.deleteLayer")}
                  </Button>
                ) : null}
              </div>
            ) : null}

            {tab === "style" ? (
              <StyleTab
                selected={selected}
                onLiveChange={onLiveChange}
                onCommitChange={onCommitChange}
                onCommit={onCommit}
              />
            ) : null}

            {tab === "color" ? (
              <ColorTab
                selected={selected}
                onCommitChange={onCommitChange}
              />
            ) : null}

            {tab === "align" ? (
              <AlignTab selected={selected} onCommitChange={onCommitChange} />
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}

function StyleTab({
  selected,
  onLiveChange,
  onCommitChange,
  onCommit,
}: {
  selected: TextLayer;
  onLiveChange: (patch: Partial<TextLayer>) => void;
  onCommitChange: (patch: Partial<TextLayer>) => void;
  onCommit: () => void;
}) {
  const { t } = useI18n();
  const percent = Math.round(selected.font_size * 1000) / 10;
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-2">
        {AD_FONTS.map((font) => (
          <button
            key={font.id}
            type="button"
            onClick={() => onCommitChange({ font_family: font.id })}
            className={cn(
              "rounded-2xl border px-3 py-2 text-start",
              selected.font_family === font.id
                ? "border-brand-400 bg-brand-50"
                : "border-ink-200 bg-surface",
            )}
          >
            <span className="block text-sm font-bold" style={{ fontFamily: font.family }}>
              {t(`ad.font.${font.id}.label` as TranslationKey)}
            </span>
            <span className="text-xs text-ink-400">
              {t(`ad.font.${font.id}.vibe` as TranslationKey)}
            </span>
          </button>
        ))}
      </div>
      <div className="flex gap-2">
        <Button
          variant={selected.font_weight === 400 ? "secondary" : "outline"}
          className="flex-1"
          onClick={() => onCommitChange({ font_weight: 400 })}
        >
          {t("editor.weightRegular")}
        </Button>
        <Button
          variant={selected.font_weight === 700 ? "secondary" : "outline"}
          className="flex-1"
          onClick={() => onCommitChange({ font_weight: 700 })}
        >
          {t("editor.weightBold")}
        </Button>
      </div>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          className="size-11 p-0"
          onClick={() =>
            onCommitChange({ font_size: selected.font_size - 0.008 })
          }
        >
          −
        </Button>
        <input
          type="range"
          min={2.4}
          max={22}
          step={0.2}
          value={percent}
          onChange={(event) =>
            onLiveChange({ font_size: Number(event.target.value) / 100 })
          }
          onPointerUp={onCommit}
          className="flex-1"
          aria-label={t("editor.fontSize")}
        />
        <Button
          variant="outline"
          className="size-11 p-0"
          onClick={() =>
            onCommitChange({ font_size: selected.font_size + 0.008 })
          }
        >
          +
        </Button>
      </div>
    </div>
  );
}

function ColorTab({
  selected,
  onCommitChange,
}: {
  selected: TextLayer;
  onCommitChange: (patch: Partial<TextLayer>) => void;
}) {
  const { t } = useI18n();
  const backgrounds: { id: TextLayerBackground; label: string }[] = [
    { id: "none", label: t("editor.bgNone") },
    { id: "pill", label: t("editor.bgPill") },
  ];
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-2">
        {SWATCHES.map((color) => (
          <button
            key={color}
            type="button"
            aria-label={color}
            onClick={() => onCommitChange({ color })}
            className={cn(
              "size-11 rounded-full border",
              selected.color.toLowerCase() === color ? "ring-2 ring-brand-500" : "border-ink-200",
            )}
            style={{ background: color }}
          />
        ))}
        <input
          type="color"
          value={selected.color.length === 7 ? selected.color : "#ffffff"}
          onChange={(event) => onCommitChange({ color: event.target.value })}
          className="size-11 cursor-pointer rounded-full border border-ink-200"
          aria-label={t("editor.customColor")}
        />
      </div>
      <div className="flex gap-2">
        {backgrounds.map((item) => (
          <Button
            key={item.id}
            variant={selected.background === item.id ? "secondary" : "outline"}
            className="flex-1"
            onClick={() =>
              onCommitChange({
                background: item.id,
                background_color:
                  item.id === "none" ? selected.background_color : selected.background_color || "#000000",
                background_opacity: item.id === "none" ? selected.background_opacity : 0.55,
              })
            }
          >
            {item.label}
          </Button>
        ))}
      </div>
    </div>
  );
}

function AlignTab({
  selected,
  onCommitChange,
}: {
  selected: TextLayer;
  onCommitChange: (patch: Partial<TextLayer>) => void;
}) {
  const { t } = useI18n();
  const options: { id: TextLayerAlign; label: string }[] = [
    { id: "right", label: t("editor.alignRight") },
    { id: "center", label: t("editor.alignCenter") },
    { id: "left", label: t("editor.alignLeft") },
  ];
  return (
    <div className="flex gap-2">
      {options.map((item) => (
        <Button
          key={item.id}
          variant={selected.text_align === item.id ? "secondary" : "outline"}
          className="flex-1"
          onClick={() => onCommitChange({ text_align: item.id })}
        >
          {item.label}
        </Button>
      ))}
    </div>
  );
}

export type { TabId };
