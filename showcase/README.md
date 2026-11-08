# Andromeda v2 interactive showcase

Repository-backed presentation for the Andromeda v2 experimental flight
platform. It combines the vehicle architecture, a clearly labelled historical
flight-sizing replay, end-to-end subsystem diagrams, and the current
verification status in one responsive experience.

## Prerequisites

- Node.js `>=22.13.0`

## Quick Start

```bash
npm install
npm run dev
npm run build
```

## Engineering-data policy

- Values come from the committed CONOPS, integration manifests and historical
  simulation evidence.
- Preliminary, historical and interpolated values are visibly identified.
- The site is a communication surface, not verification evidence and not a
  substitute for rerunning the current flight models.

## Useful Commands

- `npm run dev`: start local development
- `npm run build`: verify the vinext build output
- `npm test`: build and verify the server-rendered showcase
