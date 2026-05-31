"use client";

import { AuthProvider } from "@/lib/auth-store";
import { CodeRefOverlay } from "@/components/code-ref-overlay";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <CodeRefOverlay />
      {children}
    </AuthProvider>
  );
}
