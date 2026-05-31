"use client";

import { type FormEvent, useState } from "react";
import Link from "next/link";

import { AuthShell } from "@/components/auth-shell";
import { resendPhone, verifyPhone } from "@/lib/api";
import { useAuth } from "@/lib/auth-store";

export default function VerifyPhonePage() {
  const { token } = useAuth();
  const [code, setCode] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) {
      setError("Login required");
      return;
    }
    try {
      setIsLoading(true);
      setError(null);
      const result = await verifyPhone(code, token);
      setStatus(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setIsLoading(false);
    }
  }

  async function onResend() {
    if (!token) {
      setError("Login required");
      return;
    }
    try {
      setError(null);
      const result = await resendPhone(token);
      setStatus(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cannot resend code");
    }
  }

  return (
    <AuthShell title="Phone verification" subtitle="Input 6-digit code from backend dev logs">
      <form className="space-y-3" onSubmit={onSubmit}>
        <input className="mp-input" placeholder="123456" value={code} onChange={(e) => setCode(e.target.value)} maxLength={6} />
        {error ? <p className="mp-error">{error}</p> : null}
        {status ? <p className="text-sm text-green-700">{status}</p> : null}
        <button className="mp-btn-primary w-full" disabled={isLoading} type="submit">
          {isLoading ? "Verifying..." : "Verify phone"}
        </button>
      </form>
      <button className="mp-btn-secondary mt-3 w-full" onClick={onResend} type="button">
        Resend code
      </button>
      <p className="mt-3 text-xs text-[var(--mp-muted)]">
        Back to{" "}
        <Link className="underline decoration-orange-500 decoration-2 underline-offset-2" href="/profile">
          profile
        </Link>
      </p>
    </AuthShell>
  );
}
