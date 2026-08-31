import { auth } from "./auth"
import { NextResponse } from "next/server";

export default auth((req) => {
  const isAuth = !!req.auth;
  const path = req.nextUrl.pathname;
  const isAuthPage = path.startsWith("/auth");
  const isJudgeSurface =
    path === "/" ||
    path.startsWith("/fleet") ||
    path.startsWith("/history") ||
    path.startsWith("/brand") ||
    path.startsWith("/demo-fixtures") ||
    path.startsWith("/tutorial") ||
    path.startsWith("/setup") ||
    path.startsWith("/security") ||
    path.startsWith("/pricing");

  if (!isAuth && !isAuthPage && !isJudgeSurface) {
    return NextResponse.redirect(new URL("/auth/login", req.url));
  }

  // Redirect authenticated users away from auth pages
  if (isAuth && isAuthPage) {
    return NextResponse.redirect(new URL("/", req.url));
  }

  return NextResponse.next();
})

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
}
