"use client";

import Link from "next/link";
import { useEffect } from "react";
import { Container } from "@/components/layout/Container";
import { Logo } from "@/components/layout/Logo";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ArrowForwardIcon } from "@/components/ui/icons";
import { track } from "@/lib/analytics/track";
import { CATEGORY_EXAMPLES, HERO_EXAMPLE } from "@/lib/content/landingExamples";
import { toPersianDigits } from "@/lib/format/persian";
import { AdCanvas } from "@/features/campaign/ad-renderer/AdCanvas";
import { BeforeAfter } from "./BeforeAfter";

const HOW_IT_WORKS = [
  {
    title: "عکس محصولت رو آپلود کن",
    description: "یه عکس ساده با موبایل هم کافیه.",
  },
  {
    title: "سبک تبلیغت رو انتخاب کن",
    description: "با چند سؤال ساده، بدون هیچ دانش فنی.",
  },
  {
    title: "کمپین آماده تحویل بگیر",
    description: "پست، استوری، کاروسل، کپشن و ایده ریلز.",
  },
];

const DELIVERABLES = [
  { title: "پست فید", emoji: "🖼", description: "نسبت ۴:۵ با تیتر فارسی" },
  { title: "استوری", emoji: "📱", description: "نسبت ۹:۱۶ آماده انتشار" },
  { title: "کاروسل", emoji: "🎞", description: "سه اسلاید پشت سر هم" },
  { title: "کپشن", emoji: "✍️", description: "سه لحن مختلف با هشتگ" },
  { title: "ایده ریلز", emoji: "🎬", description: "سناریوی کوتاه ۱۰ تا ۱۵ ثانیه" },
];

export function LandingPage() {
  useEffect(() => {
    track("landing_viewed");
  }, []);

  return (
    <div className="min-h-dvh bg-ink-50">
      <SiteHeader />

      <main>
        <section className="relative overflow-hidden">
          <div
            className="pointer-events-none absolute inset-x-0 top-0 h-96"
            style={{
              background:
                "radial-gradient(80% 60% at 70% 0%, rgba(124,58,237,0.16) 0%, transparent 70%)",
            }}
            aria-hidden="true"
          />
          <Container size="lg" className="relative py-10 sm:py-16">
            <div className="grid items-center gap-10 lg:grid-cols-[1fr_1.05fr]">
              <div className="animate-fade-up text-center lg:text-start">
                <span className="inline-flex items-center gap-2 rounded-full border border-brand-200 bg-white px-3 py-1.5 text-xs font-semibold text-brand-700">
                  ✨ مخصوص فروشنده‌های اینستاگرام
                </span>

                <h1 className="mt-5 text-3xl font-extrabold leading-[1.5] text-ink-900 sm:text-4xl lg:text-5xl">
                  از عکس محصولت،{" "}
                  <span className="text-gradient">تبلیغ اینستاگرام</span> بساز
                </h1>

                <p className="mx-auto mt-4 max-w-md text-base leading-8 text-ink-500 lg:mx-0">
                  عکس محصولت رو بده؛ پست، استوری، کپشن و ایده ریلز آماده بگیر.
                </p>

                <div className="mt-7 flex flex-col items-center gap-3 sm:flex-row lg:justify-start">
                  <Link href="/create" className="w-full sm:w-auto">
                    <Button
                      size="lg"
                      fullWidth
                      iconEnd={<ArrowForwardIcon width={18} height={18} />}
                    >
                      اولین کمپینت رو رایگان بساز
                    </Button>
                  </Link>
                  <span className="text-xs text-ink-400">
                    بدون نیاز به کارت بانکی
                  </span>
                </div>
              </div>

              <div className="animate-fade-up">
                <BeforeAfter example={HERO_EXAMPLE} />
                <p className="mt-4 text-center text-xs text-ink-400">
                  همین عکس ساده، تبدیل شد به یک تبلیغ آماده انتشار.
                </p>
              </div>
            </div>
          </Container>
        </section>

        <section className="py-12 sm:py-16">
          <Container size="lg">
            <h2 className="text-center text-2xl font-extrabold text-ink-900">
              برای هر کسب‌وکاری
            </h2>
            <p className="mt-2 text-center text-sm leading-7 text-ink-500">
              چند نمونه از کمپین‌هایی که می‌تونی بسازی.
            </p>

            <div className="mt-8 grid gap-5 sm:grid-cols-3">
              {CATEGORY_EXAMPLES.map((example) => (
                <div key={example.id} className="flex flex-col gap-3">
                  <div className="overflow-hidden rounded-3xl shadow-soft">
                    <AdCanvas spec={example.spec} width={1080} height={1350} />
                  </div>
                  <span className="text-center text-sm font-semibold text-ink-500">
                    {example.category_fa}
                  </span>
                </div>
              ))}
            </div>
          </Container>
        </section>

        <section className="bg-white py-12 sm:py-16">
          <Container size="lg">
            <h2 className="text-center text-2xl font-extrabold text-ink-900">
              چطور کار می‌کنه؟
            </h2>

            <div className="mt-8 grid gap-4 sm:grid-cols-3">
              {HOW_IT_WORKS.map((step, index) => (
                <Card key={step.title} className="p-5">
                  <span className="grid size-9 place-items-center rounded-xl bg-brand-50 text-sm font-extrabold text-brand-700">
                    {toPersianDigits(index + 1)}
                  </span>
                  <h3 className="mt-4 text-base font-bold text-ink-900">
                    {step.title}
                  </h3>
                  <p className="mt-1 text-sm leading-7 text-ink-500">
                    {step.description}
                  </p>
                </Card>
              ))}
            </div>
          </Container>
        </section>

        <section className="py-12 sm:py-16">
          <Container size="lg">
            <h2 className="text-center text-2xl font-extrabold text-ink-900">
              چه چیزهایی دریافت می‌کنی؟
            </h2>

            <div className="mt-8 grid gap-3 sm:grid-cols-3 lg:grid-cols-5">
              {DELIVERABLES.map((item) => (
                <Card key={item.title} className="p-4 text-center">
                  <span className="text-2xl" aria-hidden="true">
                    {item.emoji}
                  </span>
                  <h3 className="mt-2 text-sm font-bold text-ink-900">
                    {item.title}
                  </h3>
                  <p className="mt-1 text-xs leading-6 text-ink-400">
                    {item.description}
                  </p>
                </Card>
              ))}
            </div>
          </Container>
        </section>

        <section className="pb-16">
          <Container size="md">
            <div className="rounded-[2rem] bg-gradient-to-bl from-brand-700 via-brand-600 to-coral-500 p-8 text-center text-white shadow-lift sm:p-12">
              <h2 className="text-2xl font-extrabold sm:text-3xl">
                اولین کمپینت رایگانه
              </h2>
              <p className="mx-auto mt-3 max-w-md text-sm leading-8 text-white/85">
                کمتر از دو دقیقه طول می‌کشه. عکس محصولت رو بده و نتیجه رو ببین.
              </p>
              <Link href="/create" className="mt-6 inline-block">
                <Button size="lg" variant="outline" className="bg-white">
                  شروع کن
                </Button>
              </Link>
            </div>
          </Container>
        </section>
      </main>

      <footer className="border-t border-ink-100 bg-white py-8">
        <Container size="lg" className="flex flex-col items-center gap-3 text-center">
          <Logo />
          <p className="text-xs leading-6 text-ink-400">
            ساخت کمپین تبلیغاتی اینستاگرام برای کسب‌وکارهای کوچک فارسی‌زبان.
          </p>
        </Container>
      </footer>
    </div>
  );
}
