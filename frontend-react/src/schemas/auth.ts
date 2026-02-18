import { z } from "zod";

export const registerSchema = z.object({
  firstName: z.string().min(2, "Imię musi mieć co najmniej 2 znaki"),
  lastName: z.string().min(2, "Nazwisko musi mieć co najmniej 2 znaki"),
  email: z.string().email("Nieprawidłowy adres email"),
  address: z.string().min(5, "Adres jest wymagany"),
  dateOfBirth: z.string().refine((date) => !isNaN(Date.parse(date)), {
    message: "Nieprawidłowa data urodzenia",
  }),
  password: z.string().min(6, "Hasło musi mieć co najmniej 6 znaków"),
  confirmPassword: z.string().min(6, "Potwierdź hasło"),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Hasła muszą być identyczne",
  path: ["confirmPassword"],
});

export type RegisterSchema = z.infer<typeof registerSchema>;
