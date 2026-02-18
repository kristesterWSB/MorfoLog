import { z } from "zod";

export const profileSchema = z.object({
  firstName: z.string().min(2, "Imię musi mieć co najmniej 2 znaki"),
  lastName: z.string().min(2, "Nazwisko musi mieć co najmniej 2 znaki"),
  email: z.string().email("Nieprawidłowy adres email"),
  address: z.string().min(5, "Adres jest wymagany"),
  dateOfBirth: z.string().refine((date) => !isNaN(Date.parse(date)), {
    message: "Nieprawidłowa data urodzenia",
  }),
});

export type ProfileSchema = z.infer<typeof profileSchema>;
