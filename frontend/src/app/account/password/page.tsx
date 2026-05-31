"use client";

import { type FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { changePassword } from "@/lib/api";
import { useAuth } from "@/lib/auth-store";
import { changePasswordSchema } from "@/lib/validation";

export default function PasswordPage() {
  const { token } = useAuth();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) {
      router.push("/login");
      return;
    }

    const parsed = changePasswordSchema.safeParse({ currentPassword, newPassword, confirmPassword });
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? "Invalid form");
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      const result = await changePassword(token, parsed.data.currentPassword, parsed.data.newPassword);
      setMessage(result.message);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Password change failed");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="mp-shell min-h-screen flex items-center justify-center">
      <section className="mp-card w-full max-w-md p-6">
        <h1 className="text-2xl font-bold">Change password</h1>
        <p className="mt-1 text-sm text-[var(--mp-muted)]">Current password is required.</p>
        <form className="mt-4 space-y-3" onSubmit={onSubmit}>
          <input
            className="mp-input"
            type="password"
            placeholder="Current password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
          />
          <input className="mp-input" type="password" placeholder="New password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
          <input
            className="mp-input"
            type="password"
            placeholder="Confirm new password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
          />
          {error ? <p className="mp-error">{error}</p> : null}
          {message ? <p className="text-sm text-green-700">{message}</p> : null}
          <button className="mp-btn-primary w-full" disabled={isLoading} type="submit">
            {isLoading ? "Saving..." : "Save new password"}
          </button>
        </form>
        <Link className="mt-4 inline-block text-sm underline decoration-orange-500 decoration-2 underline-offset-2" href="/profile">
          Back to profile
        </Link>
      </section>
    </main>
  );
}
