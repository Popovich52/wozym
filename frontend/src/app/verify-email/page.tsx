"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { AuthShell } from "@/components/auth-shell";
import { verifyEmail } from "@/lib/api";

export default function VerifyEmailPage() {
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
