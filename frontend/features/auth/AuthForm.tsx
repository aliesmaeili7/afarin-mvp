"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { TextField } from "@/components/ui/Field";
import { GoogleIcon, SparkleIcon } from "@/components/ui/icons";
import { useToast } from "@/components/ui/Toast";
import { useDisplayError, useI18n } from "@/lib/i18n/PreferencesProvider";
import type { Session } from "@/types/domain";

const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const MIN_PASSWORD = 8;

export function AuthForm({
  mode = "login",
  submitLabel,
  verifyLabel,
  googleLabel,
  onVerified,
  onGoogle,
  onEmailStart,
}: {
  mode?: "login" | "signup";
  submitLabel: string;
  verifyLabel?: string;
  googleLabel?: string;
  onVerified: (session: Session) => Promise<void>;
  onGoogle: () => Promise<void>;
  onEmailStart?: (method: "password" | "code") => void;
}) {
  const { toast } = useToast();
  const { t } = useI18n();
  const displayError = useDisplayError();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [step, setStep] = useState<"password" | "code" | "reset">("password");
  const [resetSent, setResetSent] = useState(false);
  const [code, setCode] = useState("");
  const [codeError, setCodeError] = useState<string | null>(null);

  async function handlePassword() {
    const address = email.trim().toLowerCase();
    if (!EMAIL_PATTERN.test(address)) {
      setEmailError(t("errors.invalidEmail"));
      return;
    }
    if (password.length < MIN_PASSWORD) {
      setPasswordError(t("errors.passwordMin"));
      return;
    }
    if (mode === "signup" && password !== confirm) {
      setPasswordError(t("errors.passwordMismatch"));
      return;
    }

    setSubmitting(true);
    onEmailStart?.("password");
    try {
      const session =
        mode === "signup"
          ? await api.signUpWithPassword({ email: address, password })
          : await api.signInWithPassword({ email: address, password });
      await onVerified(session);
    } catch (caught) {
      toast(displayError(caught), "error");
      setSubmitting(false);
    }
  }

  async function handleSendCode() {
    const address = email.trim().toLowerCase();
    if (!EMAIL_PATTERN.test(address)) {
      setEmailError(t("errors.invalidEmail"));
      return;
    }

    setSubmitting(true);
    onEmailStart?.("code");
    try {
      await api.requestEmailCode({ email: address });
      setStep("code");
    } catch (caught) {
      toast(displayError(caught), "error");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleVerifyCode() {
    const entered = code.trim();
    if (!/^\d{6}$/.test(entered)) {
      setCodeError(t("errors.codeIncomplete"));
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
      setCodeError(displayError(caught));
      setSubmitting(false);
    }
  }

  async function handleForgotPassword() {
    const address = email.trim().toLowerCase();
    if (!EMAIL_PATTERN.test(address)) {
      setEmailError(t("errors.invalidEmail"));
      return;
    }

    setSubmitting(true);
    try {
      await api.requestPasswordReset({
        email: address,
        redirect_to: new URL("/auth/reset-password", window.location.origin).toString(),
      });
      setResetSent(true);
    } catch (caught) {
      toast(displayError(caught), "error");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleGoogle() {
    setSubmitting(true);
    try {
      await onGoogle();
    } catch (caught) {
      toast(displayError(caught), "error");
      setSubmitting(false);
    }
  }

  if (step === "code") {
    return (
      <Card className="flex flex-col gap-4 p-5">
        <div className="text-center">
          <p className="text-sm font-bold text-foreground">{t("auth.codeSentTitle")}</p>
          <p className="mt-1 text-sm leading-7 text-muted">
            {t("auth.codeSentBody", { email })}
          </p>
        </div>

        <TextField
          label={t("auth.codeLabel")}
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          dir="ltr"
          placeholder={t("auth.codePlaceholder")}
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
            setStep("password");
            setCode("");
            setCodeError(null);
          }}
        >
          {t("auth.passwordLogin")}
        </Button>
      </Card>
    );
  }

  if (step === "reset") {
    return (
      <Card className="flex flex-col gap-4 p-5">
        <div className="text-center">
          <p className="text-sm font-bold text-foreground">{t("auth.resetTitle")}</p>
          <p className="mt-1 text-sm leading-7 text-muted">
            {resetSent ? t("auth.resetSent") : t("auth.resetBody")}
          </p>
        </div>

        {resetSent ? (
          <Button
            variant="ghost"
            size="sm"
            fullWidth
            onClick={() => {
              setStep("password");
              setResetSent(false);
            }}
          >
            {t("auth.backToLogin")}
          </Button>
        ) : (
          <>
            <TextField
              label={t("auth.email")}
              type="email"
              inputMode="email"
              autoComplete="email"
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
              onClick={() => void handleForgotPassword()}
            >
              {t("auth.sendLink")}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              fullWidth
              disabled={submitting}
              onClick={() => setStep("password")}
            >
              {t("auth.backToLogin")}
            </Button>
          </>
        )}
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
        {googleLabel ?? t("auth.google")}
      </Button>

      <div className="flex items-center gap-3 text-xs text-ink-400">
        <span className="h-px flex-1 bg-ink-200" />
        {t("common.or")}
        <span className="h-px flex-1 bg-ink-200" />
      </div>

      <TextField
        label={t("auth.email")}
        type="email"
        inputMode="email"
        autoComplete="email"
        placeholder="you@example.com"
        value={email}
        error={emailError}
        onChange={(event) => {
          setEmail(event.target.value);
          setEmailError(null);
        }}
      />

      <TextField
        label={t("auth.password")}
        type="password"
        autoComplete={mode === "signup" ? "new-password" : "current-password"}
        value={password}
        error={mode === "signup" ? null : passwordError}
        hint={mode === "signup" ? t("auth.passwordHint") : undefined}
        onChange={(event) => {
          setPassword(event.target.value);
          setPasswordError(null);
        }}
      />

      {mode === "signup" ? (
        <TextField
          label={t("auth.confirmPassword")}
          type="password"
          autoComplete="new-password"
          value={confirm}
          error={passwordError}
          onChange={(event) => {
            setConfirm(event.target.value);
            setPasswordError(null);
          }}
        />
      ) : null}

      <Button
        size="lg"
        fullWidth
        loading={submitting}
        onClick={() => void handlePassword()}
        iconStart={<SparkleIcon width={18} height={18} />}
      >
        {submitLabel}
      </Button>

      {mode === "login" ? (
        <Button
          variant="ghost"
          size="sm"
          fullWidth
          disabled={submitting}
          onClick={() => {
            setStep("reset");
            setResetSent(false);
            setEmailError(null);
          }}
        >
          {t("auth.forgot")}
        </Button>
      ) : null}

      <Button
        variant="ghost"
        size="sm"
        fullWidth
        disabled={submitting}
        onClick={() => void handleSendCode()}
      >
        {t("auth.emailCode")}
      </Button>
    </Card>
  );
}
