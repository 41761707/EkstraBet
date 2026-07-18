import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { getApiBaseUrl, getAuthCookieName } from "@/lib/auth";

interface RouteParams {
  params: Promise<{ path: string[] }>;
}

async function proxyRequest(
  request: Request,
  pathSegments: string[],
): Promise<Response> {
  const upstreamPath = pathSegments.join("/");
  const incomingUrl = new URL(request.url);
  const targetUrl = new URL(upstreamPath, `${getApiBaseUrl()}/`);
  targetUrl.search = incomingUrl.search;

  const headers = new Headers();
  const accept = request.headers.get("accept");
  if (accept) {
    headers.set("accept", accept);
  }
  const contentType = request.headers.get("content-type");
  if (contentType) {
    headers.set("content-type", contentType);
  }

  const jar = await cookies();
  const token = jar.get(getAuthCookieName())?.value;
  if (token) {
    headers.set("authorization", `Bearer ${token}`);
  }

  const method = request.method.toUpperCase();
  const init: RequestInit = {
    method,
    headers,
    cache: "no-store",
  };

  if (method !== "GET" && method !== "HEAD") {
    init.body = await request.arrayBuffer();
  }

  const upstream = await fetch(targetUrl.toString(), init);
  const responseHeaders = new Headers();
  const upstreamContentType = upstream.headers.get("content-type");
  if (upstreamContentType) {
    responseHeaders.set("content-type", upstreamContentType);
  }

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

export async function GET(request: Request, { params }: RouteParams) {
  const { path } = await params;
  return proxyRequest(request, path);
}

export async function POST(request: Request, { params }: RouteParams) {
  const { path } = await params;
  return proxyRequest(request, path);
}

export async function PUT(request: Request, { params }: RouteParams) {
  const { path } = await params;
  return proxyRequest(request, path);
}

export async function PATCH(request: Request, { params }: RouteParams) {
  const { path } = await params;
  return proxyRequest(request, path);
}

export async function DELETE(request: Request, { params }: RouteParams) {
  const { path } = await params;
  return proxyRequest(request, path);
}
