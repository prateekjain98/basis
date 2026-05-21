import { type NextRequest, NextResponse } from "next/server";

export async function proxy(_request: NextRequest) {
  // Auth disabled — allow all requests
  return NextResponse.next();
}

export const config = {
  matcher: [
    "/",
    "/chat/:id",
    "/api/:path*",
    "/login",
    "/register",
    "/((?!_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)",
  ],
};
