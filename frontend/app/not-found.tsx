"use client";

import Link from "next/link";
import { Container } from "@/components/layout/Container";
import { Logo } from "@/components/layout/Logo";
import { PreferencesTrigger } from "@/components/layout/PreferencesSheet";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/Feedback";
import { useI18n } from "@/lib/i18n/PreferencesProvider";

export default function NotFound() {
  const { t } = useI18n();
  return (
    <div className="flex min-h-dvh flex-col bg-background">
      <header className="border-b border-border bg-surface">
        <Container size="lg" className="flex h-16 items-center justify-between">
          <Logo />
          <PreferencesTrigger />
        </Container>
      </header>
      <Container size="sm" className="flex flex-1 items-center py-16">
        <div className="w-full">
          <EmptyState
            title={t("errors.notFoundTitle")}
            description={t("errors.notFoundDescription")}
            action={
              <Link href="/">
                <Button>{t("errors.notFoundAction")}</Button>
              </Link>
            }
          />
        </div>
      </Container>
    </div>
  );
}
