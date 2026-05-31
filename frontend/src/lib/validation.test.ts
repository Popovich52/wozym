import { describe, expect, it } from "vitest";

import { changePasswordSchema, loginSchema, registerSchema } from "@/lib/validation";

describe("validation", () => {
  it("rejects invalid register data", () => {
    const result = registerSchema.safeParse({
      name: "",
      email: "bad",
      phone: "",
      password: "123",
      confirmPassword: "456",
    });
    expect(result.success).toBe(false);
  });

  it("accepts valid login", () => {
    const result = loginSchema.safeParse({ login: "user@example.com", password: "secret" });
    expect(result.success).toBe(true);
  });

  it("enforces change-password confirmation", () => {
    const result = changePasswordSchema.safeParse({
      currentPassword: "Secret123",
      newPassword: "NewSecret123",
      confirmPassword: "Mismatch",
    });
    expect(result.success).toBe(false);
  });
});
