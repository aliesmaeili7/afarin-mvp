"use client";

import { useState } from "react";
import { api, toPersianError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { TextField } from "@/components/ui/Field";
import { GoogleIcon, SparkleIcon } from "@/components/ui/icons";
import { useToast } from "@/components/ui/Toast";
import type { Session } from "@/types/domain";

export function AuthForm({
  submitLabel,
  verifyLabel,
  googleLabel = "ادامه با گوگل",
  onVerified,
  onGoogle,
  onRequestCode,
}: {
  submitLabel: string;
  verifyLabel?: string;
  googleLabel?: string;
  onVerified: (session: Session) => Promise<void>;
  onGoogle: () => Promise<void>;
  onRequestCode?: () => void;
}) {
  const { toast } = useToast();
  const [email, setEmail] = useState("");
  const [emailError, setEmailError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [step, setStep] = useState<"identify" | "code">("identify");
  const [code, setCode] = useState("");
  const [codeError, setCodeError] = useState<string | null>(null);

  async function handleSendCode() {
    const address = email.trim().toLowerCase();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(address)) {
      setEmailError("ایمیل معتبر وارد کن.");
      return;
    }

    setSubmitting(true);
    onRequestCode?.();
    try {
      await api.requestEmailCode({ email: address });
      setStep("code");
    } catch (caught) {
      toast(toPersianError(caught), "error");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleVerifyCode() {
    const entered = code.trim();
    if (!/^\d{6}$/.test(entered)) {
      setCodeError("کد ۶ رقمی رو کامل وارد کن.");
      return;
    }

    setSubmitting(true);
    try {
      const session = await api.verifyEmailCode({
        email: email.trim().toLowerCase(),
        code: entered,
      });
      await onVerified(session);
    } catch (caught) {
      setCodeError(toPersianError(caught));
      setSubmitting(false);
    }
  }

  async function handleGoogle() {
    setSubmitting(true);
    try {
      await onGoogle();
    } catch (caught) {
      toast(toPersianError(caught), "error");
      setSubmitting(false);
    }
  }

  if (step === "code") {
    return (
      <Card className="flex flex-col gap-4 p-5">
        <div className="text-center">
          <p className="text-sm font-bold text-ink-900">کد رو برات فرستادیم</p>
          <p className="mt-1 text-sm leading-7 text-ink-500">
            کد ۶ رقمی که به <span dir="ltr">{email}</span> ارسال شد رو وارد کن.
          </p>
        </div>

        <TextField
          label="کد تأیید"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          dir="ltr"
          placeholder="۱۲۳۴۵۶"
          value={code}
          error={codeError}
          className="text-center text-lg tracking-[0.5em]"
          onChange={(event) => {
            setCode(event.target.value.replace(/\D/g, "").slice(0, 6));
            setCodeError(null);
          }}
        />

        <Button
          size="lg"
          fullWidth
          loading={submitting}
          onClick={() => void handleVerifyCode()}
          iconStart={<SparkleIcon width={18} height={18} />}
        >
          {verifyLabel ?? submitLabel}
        </Button>

        <Button
          variant="ghost"
          size="sm"
          fullWidth
          disabled={submitting}
          onClick={() => {
            setStep("identify");
            setCode("");
            setCodeError(null);
          }}
        >
          ایمیل رو اشتباه زدم
        </Button>
      </Card>
    );
  }

  return (
    <Card className="flex flex-col gap-4 p-5">
      <Button
        variant="outline"
        size="lg"
        fullWidth
        disabled={submitting}
        onClick={() => void handleGoogle()}
        iconStart={<GoogleIcon />}
      >
        {googleLabel}
      </Button>

      <div className="flex items-center gap-3 text-xs text-ink-400">
        <span className="h-px flex-1 bg-ink-200" />
        یا
        <span className="h-px flex-1 bg-ink-200" />
      </div>

      <TextField
        label="ایمیل"
        type="email"
        inputMode="email"
        placeholder="you@example.com"
        value={email}
        error={emailError}
        onChange={(event) => {
          setEmail(event.target.value);
          setEmailError(null);
        }}
      />

      <Button
        size="lg"
        fullWidth
        loading={submitting}
        onClick={() => void handleSendCode()}
        iconStart={<SparkleIcon width={18} height={18} />}
      >
        {submitLabel}
      </Button>
    </Card>
  );
}
