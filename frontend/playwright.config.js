import { defineConfig } from "playwright/test";

const baseURL = process.env.BASE_URL || "http://127.0.0.1:5173";

export default defineConfig({
  testDir: "./tests",
  timeout: 120_000,
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      testIgnore: /supabase/,
      use: {
        browserName: "chromium",
        headless: true,
        viewport: { width: 1440, height: 960 },
      },
    },
    {
      name: "supabase",
      testMatch: /supabase/,
      use: {
        browserName: "chromium",
        headless: true,
        viewport: { width: 1440, height: 960 },
      },
    },
  ],
});