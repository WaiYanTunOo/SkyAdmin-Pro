/** Admin session flow — login, CSRF, session, CSP, rate-limiting. */

export { registerLoginPageTests } from "./admin.test.parts/login_page";
export { registerLoginPostTests } from "./admin.test.parts/login_post";
export { registerSessionGateTests } from "./admin.test.parts/session_gate";
export { registerLogoutTests } from "./admin.test.parts/logout";
export { registerIpBlockTests } from "./admin.test.parts/ip_block";
export { registerCspTests } from "./admin.test.parts/csp";
export { registerSessionApiTests } from "./admin.test.parts/session_api";
export { registerDashboardJsSmokeTests } from "./admin.test.parts/dashboard_js";

import { registerLoginPageTests } from "./admin.test.parts/login_page";
import { registerLoginPostTests } from "./admin.test.parts/login_post";
import { registerSessionGateTests } from "./admin.test.parts/session_gate";
import { registerLogoutTests } from "./admin.test.parts/logout";
import { registerIpBlockTests } from "./admin.test.parts/ip_block";
import { registerCspTests } from "./admin.test.parts/csp";
import { registerSessionApiTests } from "./admin.test.parts/session_api";
import { registerDashboardJsSmokeTests } from "./admin.test.parts/dashboard_js";

registerLoginPageTests();
registerLoginPostTests();
registerSessionGateTests();
registerLogoutTests();
registerIpBlockTests();
registerCspTests();
registerSessionApiTests();
registerDashboardJsSmokeTests();
