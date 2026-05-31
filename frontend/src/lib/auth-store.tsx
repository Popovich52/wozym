"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { me, type User } from "@/lib/api";

const TOKEN_KEY = "wozym_access_token";

type AuthContextValue = {
  token: string | null;
  user: User | null;
  isReady: boolean;
  setAuth: (token: string, user: User) => void;
  clearAuth: () => void;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(TOKEN_KEY);
  });
  const [user, setUser] = useState<User | null>(null);
  const [isReady, setIsReady] = useState(() => {
    if (typeof window === "undefined") return false;
    return window.localStorage.getItem(TOKEN_KEY) === null;
  });

  useEffect(() => {
    if (!token) return;
    me(token)
      .then((profile) => setUser(profile))
      .catch(() => {
        window.localStorage.removeItem(TOKEN_KEY);
        setToken(null);
        setUser(null);
      })
      .finally(() => setIsReady(true));
  }, [token]);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user,
      isReady,
      setAuth: (nextToken: string, nextUser: User) => {
        setToken(nextToken);
        setUser(nextUser);
        setIsReady(true);
        window.localStorage.setItem(TOKEN_KEY, nextToken);
      },
      clearAuth: () => {
        setToken(null);
        setUser(null);
        setIsReady(true);
        window.localStorage.removeItem(TOKEN_KEY);
      },
      refreshUser: async () => {
        if (!token) return;
        const profile = await me(token);
        setUser(profile);
      },
    }),
    [isReady, token, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return ctx;
}

export function isUnauthorizedState(isReady: boolean, token: string | null) {
  return isReady && !token;
}

