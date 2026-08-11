import { toPersianDigits } from "@/lib/format/persian";
import { cn } from "./cn";

/** Wizard progress indicator, e.g. ۲ / ۵ (spec §7). */
export function Stepper({
  current,
  total,
  label,
}: {
  current: number;
  total: number;
  label?: string;
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-sm font-semibold text-ink-700">{label}</span>
        <span className="text-sm font-bold tabular-nums text-brand-600">
          {toPersianDigits(current)} / {toPersianDigits(total)}
        </span>
      </div>
      <div className="flex gap-1.5" role="progressbar" aria-valuenow={current} aria-valuemin={1} aria-valuemax={total}>
        {Array.from({ length: total }, (_, index) => (
          <span
            key={index}
            className={cn(
              "h-1.5 flex-1 rounded-full transition-colors duration-300",
              index < current ? "bg-brand-600" : "bg-ink-200",
            )}
          />
        ))}
      </div>
    </div>
  );
}

export function ProgressBar({ percent }: { percent: number }) {
  return (
    <div className="h-2.5 w-full overflow-hidden rounded-full bg-ink-200">
      <div
        className="h-full rounded-full bg-gradient-to-l from-brand-600 via-brand-500 to-coral-500 transition-[width] duration-700 ease-out"
        style={{ width: `${Math.min(100, Math.max(0, percent))}%` }}
      />
    </div>
  );
}
