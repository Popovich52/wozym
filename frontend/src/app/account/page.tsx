"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AccountCompatPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/profile");
  }, [router]);

  return (
    <main className="mp-shell min-h-screen flex items-center justify-center">
      <section className="mp-card p-6 text-sm">Redirecting to profile...</section>
    </main>
  );
}
