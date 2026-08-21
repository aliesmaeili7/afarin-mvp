import { notFound } from "next/navigation";

export default function DevLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  if (process.env.NODE_ENV === "production") {
    notFound();
  }
  return (
    <div dir="ltr" lang="en" className="min-h-dvh bg-background text-foreground">
      {children}
    </div>
  );
}
