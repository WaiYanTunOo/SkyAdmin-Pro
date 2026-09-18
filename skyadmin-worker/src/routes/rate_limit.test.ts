/** Rate limiting tests — claim endpoint and admin login. */

import { describe } from "vitest";
import { claimRateLimit } from "./rate_limit_parts/claim";
import { controlRateLimit } from "./rate_limit_parts/control";
import { adminLoginRateLimit } from "./rate_limit_parts/login";
import { pullRateLimit } from "./rate_limit_parts/pull";
import { purgeRateLimits } from "./rate_limit_parts/purge";

describe("claim rate limiting", () => {
  claimRateLimit();
});

describe("control rate limiting", () => {
  controlRateLimit();
});

describe("sync pull rate limiting", () => {
  pullRateLimit();
});

describe("purgeStaleRateLimits", () => {
  purgeRateLimits();
});

describe("admin login rate limiting", () => {
  adminLoginRateLimit();
});
