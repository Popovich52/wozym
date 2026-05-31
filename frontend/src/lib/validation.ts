import { z } from "zod";

export const registerSchema = z
  .object({
    name: z.string().min(1, "Name is required"),
    email: z.email("Invalid email"),
    phone: z.string().min(8, "Phone is required"),
    password: z.string().min(8, "Password must be at least 8 chars"),
    confirmPassword: z.string().min(8, "Password confirmation required"),
  })
  .refine((value) => value.password === value.confirmPassword, {
    path: ["confirmPassword"],
    message: "Passwords do not match",
  });

export const loginSchema = z.object({
  login: z.string().min(3, "Email or phone is required"),
  password: z.string().min(1, "Password is required"),
});

export const changePasswordSchema = z
  .object({
    currentPassword: z.string().min(1, "Current password is required"),
    newPassword: z.string().min(8, "New password must be at least 8 chars"),
    confirmPassword: z.string().min(8, "Password confirmation required"),
  })
  .refine((value) => value.newPassword === value.confirmPassword, {
    path: ["confirmPassword"],
    message: "Passwords do not match",
  });
