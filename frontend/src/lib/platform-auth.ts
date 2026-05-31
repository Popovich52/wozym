"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { platformMe, type PlatformActor } from "@/lib/api";
import { isUnauthorizedState, useAuth } from "@/lib/auth-store";

export function usePlatformGuard() {
  const { token, isReady } = useAuth();
  const router = useRouter();
  const [actor, setActor] = useState<PlatformActor | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isUnauthorizedState(isReady, token)) {
      router.push("/login");
    }
  }, [isReady, token, router]);

  useEffect(() => {
    if (!token) return;
    platformMe(token)
      .then((row) => {
        setActor(row);
        setError(null);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Platform access denied");
      })
      .finally(() => setLoading(false));
  }, [token]);

  return { token, isReady, actor, error, loading };
}
