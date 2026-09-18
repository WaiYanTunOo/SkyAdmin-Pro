/** Pricing POST handler tests. */

import { describe } from "vitest";
import { pricingGet } from "./pricing_parts/get";
import { pricingPostA } from "./pricing_parts/post_a";
import { pricingPostB } from "./pricing_parts/post_b";

describe("pricing GET", () => {
  pricingGet();
});

describe("pricing POST", () => {
  pricingPostA();
  pricingPostB();
});
