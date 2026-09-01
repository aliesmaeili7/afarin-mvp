"use client";

import { CheckIcon } from "@/components/ui/icons";
import { cn } from "@/components/ui/cn";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import type { ChatTheme } from "@/lib/api/chat/types";
import { ChatSheet } from "./primitives/ChatSheet";

export function ThemePickerSheet({
  open,
  onClose,
  themes,
  selectedId,
  onSelect,
}: {
  open: boolean;
  onClose: () => void;
  themes: ChatTheme[];
  selectedId: string | null;
  onSelect: (themeId: string | null) => void;
}) {
  const { t } = useI18n();
  const saved = themes.filter((theme) => theme.group === "saved");
  const catalog = themes.filter((theme) => theme.group === "catalog");

  return (
    <ChatSheet open={open} onClose={onClose} title={t("chat.themeTitle")}>
      <div data-chat="theme-picker" className="flex flex-col gap-5 pb-4">
        <ThemeRow
          label={t("chat.themeAuto")}
          selected={selectedId === null}
          swatch="linear-gradient(135deg, #7c3aed, #fb7263)"
          onSelect={() => {
            onSelect(null);
            onClose();
          }}
        />
        {saved.length > 0 ? (
          <section>
            <h3 className="mb-2 text-xs font-semibold text-chat-text-secondary">
              {t("chat.themeMine")}
            </h3>
            <div className="flex flex-col gap-1.5">
              {saved.map((theme) => (
                <ThemeRow
                  key={theme.id}
                  label={theme.name}
                  selected={selectedId === theme.id}
                  swatch={theme.swatch}
                  onSelect={() => {
                    onSelect(theme.id);
                    onClose();
                  }}
                />
              ))}
            </div>
          </section>
        ) : null}
        <section>
          <h3 className="mb-2 text-xs font-semibold text-chat-text-secondary">
            {t("chat.themeCatalog")}
          </h3>
          <div className="flex flex-col gap-1.5">
            {catalog.map((theme) => (
              <ThemeRow
                key={theme.id}
                label={theme.name}
                selected={selectedId === theme.id}
                swatch={theme.swatch}
                onSelect={() => {
                  onSelect(theme.id);
                  onClose();
                }}
              />
            ))}
          </div>
        </section>
      </div>
    </ChatSheet>
  );
}

function ThemeRow({
  label,
  selected,
  swatch,
  onSelect,
}: {
  label: string;
  selected: boolean;
  swatch: string;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "flex h-12 w-full items-center gap-3 rounded-chat-md px-2 text-start text-sm font-medium text-chat-text",
        selected ? "bg-chat-accent-soft" : "hover:bg-chat-surface-secondary",
      )}
    >
      <span
        className="size-8 shrink-0 rounded-full"
        style={{ background: swatch }}
        aria-hidden="true"
      />
      <span className="flex-1 truncate">{label}</span>
      {selected ? <CheckIcon width={16} height={16} className="text-chat-accent" /> : null}
    </button>
  );
}
