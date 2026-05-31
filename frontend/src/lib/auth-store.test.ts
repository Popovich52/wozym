import { describe, expect, it } from "vitest";

import { isUnauthorizedState } from "@/lib/auth-store";

describe("auth-store", () => {
  it("marks unauthorized only when app is ready and token is absent", () => {
    expect(isUnauthorizedState(false, null)).toBe(false);
    expect(isUnauthorizedState(true, "token")).toBe(false);
    expect(isUnauthorizedState(true, null)).toBe(true);
  });
});
