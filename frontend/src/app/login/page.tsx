"use client";

import { Suspense, type FormEvent, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

import { AuthShell } from "@/components/auth-shell";
import { login, platformMe } from "@/lib/api";
import { useAuth } from "@/lib/auth-store";
import { loginSchema } from "@/lib/validation";

function LoginPageContent() {
  const [loginValue, setLoginValue] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();
  const { setAuth } = useAuth();

  const isRegistered = useMemo(() => searchParams.get("registered") === "1", [searchParams]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const parsed = loginSchema.safeParse({ login: loginValue, password });
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? "Invalid form");
      return;
    }
    try {
      setIsLoading(true);
      const result = await login({ login: parsed.data.login, password: parsed.data.password });
      setAuth(result.access_token, result.user);
      try {
        await platformMe(result.access_token);
        router.push("/platform");
      } catch {
        router.push("/dashboard");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <AuthShell title="Sign in" subtitle="Use email or phone + password">
      {isRegistered ? <p className="mb-3 rounded-md border border-green-200 bg-green-50 p-2 text-xs text-green-700">Registration completed. Now sign in.</p> : null}
      <form className="space-y-3" onSubmit={onSubmit}>
        <input
          className="mp-input"
          placeholder="Email or phone"
          autoComplete="username"
          value={loginValue}
          onChange={(e) => setLoginValue(e.target.value)}
        />
        <input
          className="mp-input"
          placeholder="Password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error ? <p className="mp-error">{error}</p> : null}
        <button className="mp-btn-primary w-full" disabled={isLoading} type="submit">
          {isLoading ? "Signing in..." : "Sign in"}
        </button>
      </form>
      <p className="mt-3 text-xs text-[var(--mp-muted)]">
        Need account?{" "}
        <Link href="/register" className="underline decoration-orange-500 decoration-2 underline-offset-2">
          Register
        </Link>
      </p>
    </AuthShell>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<main className="mp-shell min-h-screen flex items-center justify-center"><section className="mp-card p-6 text-sm">Loading...</section></main>}>
      <LoginPageContent />
    </Suspense>
  );
}
