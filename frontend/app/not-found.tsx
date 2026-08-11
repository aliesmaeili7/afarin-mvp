import Link from "next/link";
import { Container } from "@/components/layout/Container";
import { Logo } from "@/components/layout/Logo";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/Feedback";

export default function NotFound() {
  return (
    <div className="flex min-h-dvh flex-col bg-ink-50">
      <header className="border-b border-ink-100 bg-white">
        <Container size="lg" className="flex h-16 items-center">
          <Logo />
        </Container>
      </header>
      <Container size="sm" className="flex flex-1 items-center py-16">
        <div className="w-full">
          <EmptyState
            title="این صفحه پیدا نشد"
            description="ممکنه آدرس اشتباه باشه یا صفحه جابه‌جا شده باشه."
            action={
              <Link href="/">
                <Button>بازگشت به صفحه اصلی</Button>
              </Link>
            }
          />
        </div>
      </Container>
    </div>
  );
}
