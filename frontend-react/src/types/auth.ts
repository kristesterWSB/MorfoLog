export interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  address: string;
  dateOfBirth: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  firstName: string;
  lastName: string;
  address: string;
  dateOfBirth: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface AuthResponse {
  accessToken: string;
  expiresIn: number;
  refreshToken: string;
  tokenType: string;
}
