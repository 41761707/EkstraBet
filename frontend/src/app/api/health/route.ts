import { NextResponse } from "next/server";

/** Simple Next.js liveness probe (no database or upstream checks). */
export async function GET() {
  return NextResponse.json({ status: "ok" });
}
