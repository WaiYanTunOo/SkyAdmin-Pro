import type { Env } from "../../db";

export function mockEnv(overrides: Partial<Env> = {}): Env {
  const result = {
    first: async () => null,
    run: async () => ({ success: true }),
    all: async () => ({ results: [] }),
  };
  return {
    DB: {
      prepare: () => ({
        ...result,
        bind: () => result,
      }),
    } as unknown as D1Database,
    LICENSE_SECRET: "test-license-secret",
    API_TOKEN: "test-api-token",
    ADMIN_PATH: "admin-test",
    ADMIN_PASS: "admin-pass",
    ...overrides,
  };
}
