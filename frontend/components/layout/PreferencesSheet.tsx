"use client";

import { Sheet } from "@/components/ui/Sheet";
import { cn } from "@/components/ui/cn";
import { SettingsIcon } from "@/components/ui/icons";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import type { ThemePreference } from "@/lib/theme/types";

export function PreferencesTrigger({ className }: { className?: string }) {
  const { t, openSettings } = useI18n();
  return (
    <button
      type="button"
      onClick={openSettings}
      aria-label={t("common.settings")}
      className={cn(
        "grid size-11 place-items-center rounded-xl text-muted transition-colors hover:bg-ink-100 hover:text-foreground sm:size-9",
        className,
      )}
    >
      <SettingsIcon width={18} height={18} />
    </button>
  );
}

export function PreferencesSheet() {
  const { t, locale, theme, setLocale, setTheme, settingsOpen, closeSettings } =
    useI18n();

  return (
    <Sheet open={settingsOpen} onClose={closeSettings} title={t("common.settings")}>
      <div className="flex flex-col gap-6">
        <fieldset>
          <legend className="mb-2 text-sm font-semibold text-foreground">
            {t("common.language")}
          </legend>
          <div className="grid grid-cols-2 gap-2">
            <Choice
              selected={locale === "fa"}
              onSelect={() => setLocale("fa")}
              label={t("common.persian")}
            />
            <Choice
              selected={locale === "en"}
              onSelect={() => setLocale("en")}
              label={t("common.english")}
            />
          </div>
        </fieldset>

        <fieldset>
          <legend className="mb-2 text-sm font-semibold text-foreground">
            {t("common.appearance")}
          </legend>
          <div className="grid grid-cols-3 gap-2">
            {(["system", "light", "dark"] as const satisfies readonly ThemePreference[]).map(
              (value) => (
                <Choice
                  key={value}
                  selected={theme === value}
                  onSelect={() => setTheme(value)}
                  label={t(`common.${value}`)}
                />
              ),
            )}
          </div>
        </fieldset>
      </div>
    </Sheet>
  );
}

function Choice({
  selected,
  onSelect,
  label,
}: {
  selected: boolean;
  onSelect: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onSelect}
      className={cn(
        "h-11 rounded-2xl border px-3 text-sm font-semibold transition-colors",
        selected
          ? "border-brand-500 bg-brand-50 text-brand-700 ring-2 ring-brand-200"
          : "border-border bg-surface text-foreground hover:border-brand-300",
      )}
    >
      {label}
    </button>
  );
}
