/** Mint CSRF into login HTML (same replace as session gate). */

import { Env } from "../../../db";
import { loginPage } from "../pages";
import { generateCsrfToken, getSessionEpoch } from "../session";

export async function loginHtmlWithCsrf(
  env: Env,
  adminPath: string,
  error?: string,
): Promise<string> {
  const epoch = await getSessionEpoch(env.DB);
  const csrfToken = await generateCsrfToken(
    env.ADMIN_PASS,
    env.ADMIN_PATH,
    epoch,
  );
  return loginPage(adminPath, error).replace(
    '<input type="hidden" name="csrf_token" value="">',
    `<input type="hidden" name="csrf_token" value="${csrfToken}">`,
  );
}
