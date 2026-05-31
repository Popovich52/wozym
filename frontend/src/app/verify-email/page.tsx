"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { AuthShell } from "@/components/auth-shell";
import { verifyEmail } from "@/lib/api";

function VerifyEmailPageContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState<"idle" | "ok" | "error">(token ? "idle" : "error");
  const [message, setMessage] = useState(token ? "Checking token..." : "Token is missing");

  useEffect(() => {
    if (!token) return;
    verifyEmail(token)
      .then((result) => {
        setStatus("ok");
        setMessage(result.message);
      })
      .catch((err) => {
        setStatus("error");
        setMessage(err instanceof Error ? err.message : "Verification failed");
      });
  }, [token]);

  return (
    <AuthShell title="Email verification" subtitle="Verification status">
      <p className={status === "error" ? "mp-error" : "text-sm"}>{message}</p>
      <div className="mt-4">
        <Link className="mp-btn-primary inline-block" href="/login">
          Go to login
        </Link>
      </div>
    </AuthShell>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<main className="mp-shell min-h-screen flex items-center justify-center"><section className="mp-card p-6 text-sm">Loading...</section></main>}>
      <VerifyEmailPageContent />
    </Suspense>
  );
}
