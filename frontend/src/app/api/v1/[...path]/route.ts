import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export const fetchCache = "force-no-store";

/**
 * Same-origin browser proxy: http://127.0.0.1:3000/api/v1/* → 127.0.0.1:8000.
 * Must forward query (?wait=false) and org headers. next.config rewrites must
 * not exist for this path — they run before this dynamic route.
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
  if (!headers.has("x-tenant-id")) {
    const fallback = req.headers.get("X-Tenant-Id");
    if (fallback) headers.set("x-tenant-id", fallback);
  }

  const method = req.method.toUpperCase();
  const hasBody = method !== "GET" && method !== "HEAD" && method !== "OPTIONS";
  const body = hasBody ? await req.arrayBuffer() : undefined;

  const upstream = await fetch(dest.toString(), {
    method,
    headers,
    body,
    cache: "no-store",
    redirect: "manual",
    ...(body ? { duplex: "half" } : {}),
  } as RequestInit);

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
