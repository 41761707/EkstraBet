import "server-only";

import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { getCurrentUser } from "@/lib/api";
import { isAuthEnabled } from "@/lib/authCookie";
import {
  FIRST_LOGIN_PATH,
  PATHNAME_HEADER,
  shouldRedirectToFirstLogin,
} from "@/lib/firstLogin";

/** Keep unfinished first-login sessions on the completion form. */
export async function redirectIfFirstLoginIncomplete(): Promise<void> {
  if (!isAuthEnabled()) {
    return;
  }
  const headerList = await headers();
  const pathname = headerList.get(PATHNAME_HEADER) ?? "";
  let isFirstLogin = false;
  try {
    const user = await getCurrentUser();
    isFirstLogin = user.first_login;
  } catch {
    return;
  }
  if (shouldRedirectToFirstLogin(true, pathname, isFirstLogin)) {
    redirect(FIRST_LOGIN_PATH);
  }
}

export async function isFirstLoginPending(): Promise<boolean> {
  if (!isAuthEnabled()) {
    return false;
  }
  try {
    const user = await getCurrentUser();
    return user.first_login;
  } catch {
    return false;
  }
}
