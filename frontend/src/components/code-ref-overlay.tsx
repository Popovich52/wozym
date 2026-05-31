"use client";

import { useEffect } from "react";

export function CodeRefOverlay() {
  useEffect(() => {
    if (process.env.NODE_ENV === "production") return;
    const codeRoot = (process.env.NEXT_PUBLIC_CODE_ROOT ?? "D:/Projects/WOzYm - AI платформа продаж").replaceAll("\\", "/");

    const buildVscodeUri = (ref: string) => {
      const trimmed = ref.trim();
      const lineMatch = trimmed.match(/:(\d+)(?::\d+)?$/);
      const line = lineMatch ? Number(lineMatch[1]) : 1;
      const filePart = lineMatch ? trimmed.slice(0, lineMatch.index) : trimmed;
      const normalizedPath = filePart.match(/^[A-Za-z]:[\\/]/) ? filePart : `${codeRoot}/${filePart}`;
      const filePath = normalizedPath.replaceAll("\\", "/");
      return `vscode://file/${encodeURI(filePath)}:${line}`;
    };

    const onClick = (event: MouseEvent) => {
      if (!event.altKey) return;
      const target = event.target;
      if (!(target instanceof Element)) return;

      const withRef = target.closest<HTMLElement>("[data-code-ref]");
      if (!withRef) return;

      const ref = withRef.dataset.codeRef;
      if (!ref) return;

      event.preventDefault();
      event.stopPropagation();
      const editorUri = buildVscodeUri(ref);
      navigator.clipboard.writeText(editorUri).catch(() => null);
      window.location.href = editorUri;
    };

    document.addEventListener("click", onClick, true);
    return () => {
      document.removeEventListener("click", onClick, true);
    };
  }, []);

  if (process.env.NODE_ENV === "production") return null;
  return null;
}

