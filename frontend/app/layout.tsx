import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

/**
 * Root layout for the PixelArt Trip Planner App Router.
 *
 * Thin composition only: imports the Tailwind entry stylesheet and defines the
 * root <html>/<body>. No business logic, no data transformation, no
 * service/API calls.
 */
export const metadata: Metadata = {
  title: "PixelArt Trip Planner",
  description:
    "Gather your party and plan your next adventure — an 8-bit collaborative trip planner.",
};

export default function RootLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
