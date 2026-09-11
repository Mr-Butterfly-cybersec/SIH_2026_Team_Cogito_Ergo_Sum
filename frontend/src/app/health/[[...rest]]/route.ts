import type { NextRequest } from "next/server";

/** Runtime proxy for the health endpoints (they live outside the `/api` prefix). */
export const dynamic = "force-dynamic";

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
  "host",
  "content-length",
]);

async function proxy(request: NextRequest, rest: string[]): Promise<Response> {
  const base = process.env.API_PROXY_TARGET ?? "http://localhost:8000";
  const suffix = rest.length ? `/${rest.join("/")}` : "";

  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) headers.set(key, value);
  });

  try {
    const upstream = await fetch(`${base}/health${suffix}${request.nextUrl.search}`, {
      method: request.method,
      headers,
      cache: "no-store",
    });
    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        "content-type": upstream.headers.get("content-type") ?? "application/json",
      },
    });
  } catch {
    return Response.json({ status: "unreachable", api: base }, { status: 502 });
  }
}

type Context = { params: Promise<{ rest?: string[] }> };

export async function GET(request: NextRequest, context: Context) {
  return proxy(request, (await context.params).rest ?? []);
}
