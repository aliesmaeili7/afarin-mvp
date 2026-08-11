import type { ReactNode } from "react";
import { cn } from "@/components/ui/cn";

/** Mobile-first: full-bleed with comfortable padding, centred on desktop. */
export function Container({
  children,
  className,
  size = "md",
}: {
  children: ReactNode;
  className?: string;
  size?: "sm" | "md" | "lg";
}) {
  const sizes = {
    sm: "max-w-xl",
    md: "max-w-3xl",
    lg: "max-w-6xl",
  } as const;

  return (
    <div className={cn("mx-auto w-full px-4 sm:px-6", sizes[size], className)}>
      {children}
    </div>
  );
}
