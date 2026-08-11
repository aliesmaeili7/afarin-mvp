"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { Container } from "@/components/layout/Container";
import { Logo } from "@/components/layout/Logo";
import { Button } from "@/components/ui/Button";
import { Stepper } from "@/components/ui/Stepper";
import { ArrowBackIcon } from "@/components/ui/icons";
import { WIZARD_TOTAL, type WizardStep } from "./wizardSteps";

/**
 * Shared wizard chrome: progress on top, content in the middle, and the primary
 * action pinned to the bottom of the viewport where a thumb can reach it.
 */
export function WizardShell({
  step,
  heading,
  description,
  children,
  footer,
  backHref,
}: {
  step: WizardStep;
  heading: string;
  description?: ReactNode;
  children: ReactNode;
  footer: ReactNode;
  backHref?: string;
}) {
  const router = useRouter();

  return (
    <div className="flex min-h-dvh flex-col bg-ink-50">
      <header className="sticky top-0 z-30 border-b border-ink-100 bg-white/90 backdrop-blur-md">
        <Container size="sm" className="pt-safe">
          <div className="flex h-14 items-center justify-between gap-2">
            {backHref ? (
              <Link href={backHref} aria-label="مرحله قبل">
                <Button variant="ghost" size="sm" className="size-11 p-0 sm:size-9">
                  <ArrowBackIcon width={18} height={18} />
                </Button>
              </Link>
            ) : (
              <Button
                variant="ghost"
                size="sm"
                className="size-11 p-0 sm:size-9"
                aria-label="بازگشت"
                onClick={() => router.push("/")}
              >
                <ArrowBackIcon width={18} height={18} />
              </Button>
            )}
            <Logo className="text-base" />
            <span className="size-11 sm:size-9" aria-hidden="true" />
          </div>
          <div className="pb-3">
            <Stepper current={step.index} total={WIZARD_TOTAL} label={step.title_fa} />
          </div>
        </Container>
      </header>

      <main className="flex-1 pb-40 sm:flex-none sm:pb-0">
        <Container size="sm" className="py-6">
          <h1 className="text-2xl font-extrabold text-ink-900 sm:text-3xl">
            {heading}
          </h1>
          {description ? (
            <p className="mt-2 text-sm leading-7 text-ink-500">{description}</p>
          ) : null}
          <div className="mt-6 animate-fade-up">{children}</div>
        </Container>
      </main>

      {/*
       * Thumb-reachable and pinned on phones. From tablet up it becomes a normal
       * block right below the content, so a tall desktop window does not show an
       * empty band between the form and its own action.
       */}
      <div className="fixed inset-x-0 bottom-0 z-30 border-t border-ink-100 bg-white/95 backdrop-blur-md sm:static sm:border-t-0 sm:bg-transparent sm:backdrop-blur-none">
        <Container size="sm" className="flex flex-col gap-2 py-3 pb-safe sm:pb-16">
          {footer}
        </Container>
      </div>
    </div>
  );
}
