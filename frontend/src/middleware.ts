export { auth as middleware } from "./auth"

/**
 * [TESTING-MODE] Middleware desactivado temporalmente.
 * Permite acceso total a todas las rutas sin login.
 */
/*
import { auth } from "./auth";
import { NextResponse } from "next/server";

export default auth((req) => {
  return NextResponse.next();
});
*/

export const config = {
    matcher: [], // No coincide con nada = middleware inactivo
};
