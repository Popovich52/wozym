"use client";

import { type FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { AuthShell } from "@/components/auth-shell";
import { register } from "@/lib/api";
import { registerSchema } from "@/lib/validation";

type FormState = {
  name: string;
  email: string;
  phone: string;
  password: string;
  confirmPassword: string;
};

const initialState: FormState = { name: "", email: "", phone: "", password: "", confirmPassword: "" };

export default function RegisterPage() {
  const [form, setForm] = useState<FormState>(initialState);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const parsed = registerSchema.safeParse(form);
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? "Invalid form");
      return;
    }

    try {
      setIsLoading(true);
      await register({
        name: parsed.data.name,
        email: parsed.data.email,
        phone: parsed.data.phone,
        password: parsed.data.password,
      });
      router.push("/login?registered=1");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <AuthShell title="Create account" subtitle="Email + phone + password">
      <form className="space-y-3" onSubmit={onSubmit}>
        <input className="mp-input" placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <input
          className="mp-input"
          placeholder="Email"
          autoComplete="email"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
        />
        <input
          className="mp-input"
          placeholder="Phone (+79991234567)"
          autoComplete="tel"
          value={form.phone}
          onChange={(e) => setForm({ ...form, phone: e.target.value })}
        />
        <input
          className="mp-input"
          placeholder="Password"
          type="password"
          autoComplete="new-password"
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
        />
        <input
          className="mp-input"
          placeholder="Confirm password"
          type="password"
          autoComplete="new-password"
          value={form.confirmPassword}
          onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })}
        />
        {error ? <p className="mp-error">{error}</p> : null}
        <button className="mp-btn-primary w-full" disabled={isLoading} type="submit">
          {isLoading ? "Creating..." : "Create account"}
        </button>
      </form>
      <p className="mt-3 text-xs text-[var(--mp-muted)]">
        Already have account?{" "}
        <Link href="/login" className="underline decoration-orange-500 decoration-2 underline-offset-2">
          Login
        </Link>
      </p>
    </AuthShell>
  );
}
