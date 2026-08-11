import Link from "next/link";
import { cn } from "@/components/ui/cn";

export function Logo({
  className,
  href = "/",
}: {
  className?: string;
  href?: string;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "inline-flex h-11 items-center gap-2 font-extrabold sm:h-9",
        className,
      )}
      aria-label="آفرین، صفحه اصلی"
    >
      <span className="grid size-9 place-items-center rounded-xl bg-gradient-to-bl from-brand-600 via-brand-500 to-coral-500 text-white shadow-soft">
        <svg viewBox="0 0 24 24" width={18} height={18} fill="currentColor" aria-hidden="true">
          <path d="M12 2.6 14 8.6l6 2-6 2-2 6-2-6-6-2 6-2 2-6z" />
        </svg>
      </span>
      <span className="text-lg tracking-tight text-ink-900">آفرین</span>
    </Link>
  );
}
