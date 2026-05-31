export type UserProfile = {
  id: number;
  email: string;
  phone: string;
  name: string | null;
  email_verified_at: string | null;
  phone_verified_at: string | null;
  status: "active" | "blocked" | "deleted";
  created_at: string;
};
