"use client";

import type {
  BuiltinEducationalTheme,
  EducationalTheme,
  EducationalThemeSpec,
} from "@/types/domain";
import { cn } from "@/components/ui/cn";
import { useI18n } from "@/lib/i18n/PreferencesProvider";

/** No theme picked: Afarin designs one. */
export type ThemeChoice =
  | { kind: "auto" }
  | { kind: "builtin"; id: string }
  | { kind: "saved"; id: string };

export const AUTO_THEME: ThemeChoice = { kind: "auto" };

export function sameChoice(a: ThemeChoice, b: ThemeChoice): boolean {
  if (a.kind !== b.kind) return false;
  return a.kind === "auto" || b.kind === "auto" || a.id === b.id;
}

/**
 * The only optional input on the creation page.
 *
 * Deliberately a single row of swatches rather than a settings panel: choosing
 * a look is one tap, and everything else about the post is inferred from the
 * prompt.
 */
export function ThemePicker({
  builtin,
  saved,
  value,
  onChange,
}: {
  builtin: BuiltinEducationalTheme[];
  saved: EducationalTheme[];
  value: ThemeChoice;
  onChange: (choice: ThemeChoice) => void;
}) {
  const { t } = useI18n();

  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className="text-sm font-semibold text-foreground">
          {t("education.themeLabel")}
        </p>
        <p className="mt-1 text-xs leading-6 text-muted">
          {t("education.themeHint")}
        </p>
      </div>

      <div className="flex gap-3 overflow-x-auto pb-2">
        <ThemeTile
          label={t("education.themeAuto")}
          selected={value.kind === "auto"}
          onSelect={() => onChange(AUTO_THEME)}
          swatch={<AutoSwatch />}
        />
        {builtin.map((theme) => (
          <ThemeTile
            key={theme.id}
            label={theme.name}
            selected={value.kind === "builtin" && value.id === theme.id}
            onSelect={() => onChange({ kind: "builtin", id: theme.id })}
            swatch={<PaletteSwatch theme={theme} />}
          />
        ))}
      </div>

      {saved.length > 0 ? (
        <div>
          <p className="text-xs font-semibold text-muted">
            {t("education.themeSaved")}
          </p>
          <div className="mt-2 flex gap-3 overflow-x-auto pb-2">
            {saved.map((theme) => (
              <ThemeTile
                key={theme.id}
                label={theme.name || t("education.themeUnnamed")}
                selected={value.kind === "saved" && value.id === theme.id}
                onSelect={() => onChange({ kind: "saved", id: theme.id })}
                swatch={<PaletteSwatch theme={theme.theme_json} />}
              />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function ThemeTile({
  label,
  selected,
  onSelect,
  swatch,
}: {
  label: string;
  selected: boolean;
  onSelect: () => void;
  swatch: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={cn(
        "flex w-24 shrink-0 flex-col gap-2 rounded-2xl border bg-surface p-2 text-center transition-all",
        selected
          ? "border-brand-500 ring-2 ring-brand-200"
          : "border-border hover:border-brand-300",
      )}
    >
      <span className="block h-16 w-full overflow-hidden rounded-xl">{swatch}</span>
      <span className="block truncate text-[11px] font-semibold text-foreground">
        {label}
      </span>
    </button>
  );
}

function PaletteSwatch({ theme }: { theme: EducationalThemeSpec }) {
  const colors = [
    theme.palette.background ?? "#f6f1ff",
    theme.palette.primary[0] ?? "#7c3aed",
    theme.palette.primary[1] ?? theme.palette.secondary[0] ?? "#22d3ee",
  ];
  return (
    <span
      className="block h-full w-full"
      style={{
        background: `linear-gradient(140deg, ${colors[0]} 0%, ${colors[1]} 60%, ${colors[2]} 100%)`,
      }}
      aria-hidden="true"
    />
  );
}

function AutoSwatch() {
  return (
    <span
      className="grid h-full w-full place-items-center bg-ink-100 text-lg"
      aria-hidden="true"
    >
      ✨
    </span>
  );
}
