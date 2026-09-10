import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI University",
  description: "Learning analytics for university students",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
