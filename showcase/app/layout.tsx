import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://andromeda-v2.plushchili.chatgpt.site"),
  title: "Andromeda v2 — Experimental Flight Platform",
  description:
    "An interactive digital twin and engineering showcase for Andromeda v2.",
  icons: {
    icon: "/og.png",
    shortcut: "/og.png",
  },
  openGraph: {
    title: "Andromeda v2 — Built to test beyond the lab",
    description: "Explore the vehicle, reference mission, connected systems and engineering evidence.",
    images: [{ url: "/og.png", width: 1734, height: 907, alt: "Andromeda v2 experimental flight platform" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Andromeda v2 — Built to test beyond the lab",
    description: "Explore the vehicle, reference mission, connected systems and engineering evidence.",
    images: ["/og.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
