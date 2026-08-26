import createMiddleware from "next-intl/middleware";
import { routing } from "./i18n/routing";

export default createMiddleware(routing);

export const config = {
  // Exclude /b/* public bot gate and API/static paths from locale middleware.
  matcher: ["/", "/(fa|en)/:path*", "/((?!api|_next|_vercel|b(?:/|$)|.*\\..*).*)"],
};
