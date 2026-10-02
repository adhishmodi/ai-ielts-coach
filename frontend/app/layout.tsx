import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI IELTS Coach",
  description: "AI-powered IELTS preparation workspace",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}