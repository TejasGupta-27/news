import { NextRequest, NextResponse } from "next/server";

const API_PROXY_URL =
  process.env.API_PROXY_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

const RESPONSE_HEADERS_TO_SKIP = [
  "connection",
  "content-length",
  "content-encoding",
  "transfer-encoding",
];

async function proxyRequest(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const upstreamPath = params.path.join("/");
  const search = request.nextUrl.search;
  const targetUrl = new URL(`/api/${upstreamPath}${search}`, API_PROXY_URL);

  const headers = new Headers(request.headers);
  headers.delete("host");

  try {
    const upstreamResponse = await fetch(targetUrl, {
      method: request.method,
      headers,
      body:
        request.method === "GET" || request.method === "HEAD"
          ? undefined
          : await request.arrayBuffer(),
      cache: "no-store",
      redirect: "manual",
    });

    const responseHeaders = new Headers(upstreamResponse.headers);
    for (const header of RESPONSE_HEADERS_TO_SKIP) {
      responseHeaders.delete(header);
    }

    return new NextResponse(upstreamResponse.body, {
      status: upstreamResponse.status,
      headers: responseHeaders,
    });
  } catch {
    return NextResponse.json(
      { detail: "Could not connect to backend. Is it running?" },
      { status: 502 }
    );
  }
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PATCH = proxyRequest;
export const PUT = proxyRequest;
export const DELETE = proxyRequest;
export const OPTIONS = proxyRequest;
