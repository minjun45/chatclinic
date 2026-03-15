import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "ChatClinic",
  description: "Grounded workspace scaffold for clinical data and medical imaging review.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
