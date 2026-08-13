import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/**
 * Browser path is http://127.0.0.1:3000/api/v1/* (same-origin).
 * next.config rewrites to localhost can hit ::1 while curl uses 127.0.0.1 —
 * two uvicorn processes, two in-memory FIFOs. Pin 127.0.0.1 and forward
 * query + org headers so wait=false and GET /runs/{id} hit the same backend.
 */
function backendOrigin(): string {
  const raw =
    process.env.BACKEND_URL ||
    process.env.API_PROXY_TARGET ||
    "http://127.0.0.1:8000";
  return raw.replace(/\/$/, "").replace("://localhost", "://127.0.0.1");
}

const PASS_HEADERS = [
  "x-tenant-id",
  "x-user-id",
  "x-roles",
  "content-type",
  "authorization",
  "accept",
];

async function proxy(req: NextRequest, ctx: { params: { path: string[] } | Promise<{ path: string[] }> }) {
  const params = await Promise.resolve(ctx.params);
  const segments = params.path || [];
  const dest = new URL(`${backendOrigin()}/api/v1/${segments.join("/")}`);
  dest.search = new URL(req.url).search;

  const headers = new Headers();
  for (const name of PASS_HEADERS) {
    const value = req.headers.get(name);
    if (value) headers.set(name, value);
  }

  const method = req.method.toUpperCase();
  const body =
    method === "GET" || method === "HEAD" || method === "OPTIONS"
      ? undefined
      : await req.arrayBuffer();

  const upstream = await fetch(dest, {
    method,
    headers,
    body,
    cache: "no-store",
    redirect: "manual",
  });

  const out = new Headers();
  const contentType = upstream.headers.get("content-type");
  if (contentType) out.set("content-type", contentType);
  out.set("cache-control", "no-store");

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: out,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const OPTIONS = proxy;
