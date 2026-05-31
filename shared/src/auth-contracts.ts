export type LoginRequest = {
  login: string;
  password: string;
};

export type RegisterRequest = {
  name?: string;
  email: string;
  phone: string;
  password: string;
};

export type AccessTokenResponse = {
  access_token: string;
  token_type: "bearer";
};
