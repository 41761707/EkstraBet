import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import {
  buildUpstreamUrl,
  isAllowedMutatingOrigin,
  isMethodAllowedForPath,
  isMutatingMethod,
  normalizeBffPath,
  resolveExpectedMutatingOrigin,
} from "@/lib/bffProxy";
import { getAuthCookieName, isAuthEnabled } from "@/lib/authCookie";
import { getApiBaseUrl, getAppOrigin } from "@/lib/runtimeConfig";

interface RouteParams {
  params: Promise<{ path: string[] }>;
}

function forbidden(detail: string): NextResponse {
  return NextResponse.json({ detail }, { status: 403 });
}

function unauthorized(detail: string): NextResponse {
  return NextResponse.json({ detail }, { status: 401 });
}

function badRequest(detail: string): NextResponse {
  return NextResponse.json({ detail }, { status: 400 });
}

async function proxyRequest(
  request: Request,
  pathSegments: string[],
): Promise<Response> {
  const method = request.method.toUpperCase();
  const pathResult = normalizeBffPath(pathSegments);
  if (!pathResult.ok || !pathResult.path) {
    return forbidden("Path is not allowed");
  }

  const upstreamPath = pathResult.path;
  if (!isMethodAllowedForPath(upstreamPath, method)) {
    return forbidden("Method is not allowed for this path");
  }

  if (isMutatingMethod(method)) {
    const origin = request.headers.get("origin");
    const expectedOrigin = resolveExpectedMutatingOrigin(
      getAppOrigin(),
      request.url,
    );
    if (!isAllowedMutatingOrigin(origin, expectedOrigin)) {
      return forbidden("Origin is not allowed");
    }
  }

  const jar = await cookies();
  const token = jar.get(getAuthCookieName())?.value;
  if (isAuthEnabled() && !token) {
    return unauthorized("Not authenticated");
  }

  const incomingUrl = new URL(request.url);
  let targetUrl: URL;
  try {
    targetUrl = buildUpstreamUrl(
      getApiBaseUrl(),
      upstreamPath,
      incomingUrl.search,
    );
  } catch {
    return badRequest("Invalid upstream configuration");
  }

  // dodatkowa ochrona: upstream musi pozostać pod bazą API
  const apiBase = new URL(`${getApiBaseUrl().replace(/\/$/, "")}/`);
  if (
    targetUrl.origin !== apiBase.origin ||
    !targetUrl.pathname.startsWith(apiBase.pathname)
  ) {
    return forbidden("Path is not allowed");
  }

  const headers = new Headers();
  const accept = request.headers.get("accept");
  if (accept) {
    headers.set("accept", accept);
  }
  const contentType = request.headers.get("content-type");
  if (contentType) {
    headers.set("content-type", contentType);
  }
  if (token) {
    headers.set("authorization", `Bearer ${token}`);
  }

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
