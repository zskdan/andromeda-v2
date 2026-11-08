import type { Metadata } from "next";
import { AndromedaShowcase } from "./components/AndromedaShowcase";

export const metadata: Metadata = {
  title: "Andromeda v2 — Experimental Flight Platform",
  description:
    "Explore the Andromeda v2 sounding rocket, its modular architecture, engineering status, and flight envelope.",
};

export default function Home() {
  return <AndromedaShowcase />;
}
