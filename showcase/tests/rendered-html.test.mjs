import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

const templateRoot = new URL("../", import.meta.url);

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the Andromeda showcase", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>Andromeda v2 — Experimental Flight Platform<\/title>/i);
  assert.match(html, /Built to test/);
  assert.match(html, /Explore the vehicle/);
  assert.match(html, /Interactive digital twin/);
  assert.match(html, /Guided story/);
  assert.match(html, /Free explore/);
  assert.match(html, /Geometry includes published dimensions and conceptual engineering envelopes/);
  assert.match(html, /Flight laboratory/);
  assert.match(html, /Engineering status/);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton|Your site is taking shape/i);
});

test("removes the starter preview and exposes product metadata", async () => {
  const [page, layout, packageJson] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
  ]);
  assert.match(page, /export const metadata:\s*Metadata/);
  assert.match(page, /<AndromedaShowcase \/>/);
  assert.match(layout, /Andromeda v2/);
  assert.match(layout, /openGraph/);
  assert.match(packageJson, /"name": "andromeda-v2-showcase"/);
  assert.doesNotMatch(packageJson, /react-loading-skeleton/);
  await assert.rejects(access(new URL("app/_sites-preview/SkeletonPreview.tsx", templateRoot)));
});
