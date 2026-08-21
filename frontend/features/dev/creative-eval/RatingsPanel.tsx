"use client";

const SCORE_FIELDS = [
  ["overall", "Overall"],
  ["identity", "Product identity"],
  ["attractiveness", "Visual attractiveness"],
  ["style_match", "Style match"],
  ["template_match", "Template match"],
  ["commercial", "Commercial usefulness"],
] as const;

const FLAGS = [
  ["random_text_logo", "random text/logo"],
  ["product_changed", "product changed too much"],
  ["anatomy_artifact", "anatomy/object artifact"],
  ["duplicated_product", "duplicated product"],
  ["bad_composition", "bad composition"],
  ["boring_generic", "boring/generic"],
  ["style_mismatch", "style mismatch"],
  ["template_mismatch", "template mismatch"],
] as const;

export type CandidateRating = {
  overall?: number;
  identity?: number;
  attractiveness?: number;
  style_match?: number;
  template_match?: number;
  commercial?: number;
  flags?: string[];
  note?: string;
};

export function RatingsPanel({
  value,
  onChange,
}: {
  value: CandidateRating;
  onChange: (next: CandidateRating) => void;
}) {
  const flags = new Set(value.flags ?? []);
  return (
    <div className="mt-3 space-y-2 text-sm">
      {SCORE_FIELDS.map(([key, label]) => (
        <label key={key} className="flex items-center justify-between gap-3">
          <span>{label}</span>
          <select
            className="rounded-md border border-border bg-surface px-2 py-1"
            value={value[key] ?? ""}
            onChange={(event) =>
              onChange({
                ...value,
                [key]: event.target.value ? Number(event.target.value) : undefined,
              })
            }
          >
            <option value="">—</option>
            {[1, 2, 3, 4, 5].map((score) => (
              <option key={score} value={score}>
                {score}
              </option>
            ))}
          </select>
        </label>
      ))}
      <div className="flex flex-wrap gap-2 pt-1">
        {FLAGS.map(([id, label]) => (
          <label key={id} className="flex items-center gap-1 text-xs">
            <input
              type="checkbox"
              checked={flags.has(id)}
              onChange={(event) => {
                const next = new Set(flags);
                if (event.target.checked) {
                  next.add(id);
                } else {
                  next.delete(id);
                }
                onChange({ ...value, flags: [...next] });
              }}
            />
            {label}
          </label>
        ))}
      </div>
      <textarea
        className="w-full rounded-md border border-border bg-surface p-2"
        rows={2}
        placeholder="Optional note"
        value={value.note ?? ""}
        onChange={(event) => onChange({ ...value, note: event.target.value })}
      />
    </div>
  );
}
