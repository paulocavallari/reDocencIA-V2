import { expect, test } from "playwright/test";

const PLAN_TITLE = "Plano E2E Automatizado";
const PLAN_PROMPT = "Gerar um plano objetivo com atividade prática e foco em inclusão.";
const TEST_IDENTIFIER = process.env.TEST_IDENTIFIER || "admin";
const TEST_PASSWORD = process.env.TEST_PASSWORD || "admin";

let page;
let context;
let createdPlanId = null;

async function loginAsAdmin() {
  await page.goto("/login", { waitUntil: "domcontentloaded" });
  await page.getByLabel(/usuário|email/i).fill(TEST_IDENTIFIER);
  await page.getByLabel(/senha/i).fill(TEST_PASSWORD);
  await page.getByRole("button", { name: /entrar/i }).click();
  await expect(page).not.toHaveURL(/\/login$/);
  await expect(page.getByText(/painel do professor/i)).toBeVisible();
}

async function cleanupPlanByTitle(title) {
  const token = await page.evaluate(() => window.localStorage.getItem("redocencia-token"));
  if (!token) {
    return;
  }

  const listResponse = await page.request.get("/api/plans", {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(listResponse.ok()).toBeTruthy();

  const plans = await listResponse.json();
  const matchingPlans = plans.filter((plan) => plan.titulo === title);

  for (const plan of matchingPlans) {
    const deleteResponse = await page.request.delete(`/api/plans/${plan.id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(deleteResponse.ok()).toBeTruthy();
  }
}

test.describe.serial("full lesson-plan flow", () => {
  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext({ viewport: { width: 1440, height: 960 }, acceptDownloads: true });
    page = await context.newPage();
    await loginAsAdmin();
    await cleanupPlanByTitle(PLAN_TITLE);
  });

  test.afterAll(async () => {
    if (createdPlanId) {
      const token = await page.evaluate(() => window.localStorage.getItem("redocencia-token"));
      if (token) {
        await page.request.delete(`/api/plans/${createdPlanId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
      }
    }

    await page?.close();
    await context?.close();
  });

  test("login keeps authenticated session", async () => {
    await page.goto("/", { waitUntil: "networkidle" });
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByRole("link", { name: /novo plano|criar novo plano/i }).first()).toBeVisible();
  });

  test("generate a lesson plan", async () => {
    await page.goto("/gerador", { waitUntil: "networkidle" });

    await page.getByLabel("Nível de Ensino").selectOption("Ensino Fundamental: Anos Finais");
    await page.getByLabel("Bimestre").selectOption("1");
    await page.getByLabel("Ano/Série").selectOption({ label: "6º Ano" });
    await page.getByLabel("Disciplina").selectOption({ label: "Ciências" });

    await expect(page.locator("fieldset.form-panel").first().locator('input[type="checkbox"]').first()).toBeVisible();
    await page.locator("fieldset.form-panel").first().locator('input[type="checkbox"]').first().check();
    await expect(page.locator("fieldset.form-panel").nth(1).locator('input[type="checkbox"]').first()).toBeEnabled();
    await page.locator("fieldset.form-panel").nth(1).locator('input[type="checkbox"]').first().check();
    await page.getByLabel("Orientações Adicionais").fill(PLAN_PROMPT);

    await page.getByRole("button", { name: /gerar plano de aula/i }).click();
    await page.waitForURL("**/editor", { timeout: 120_000 });

    const editorContent = await page.locator(".ql-editor").innerHTML();
    expect(editorContent.length).toBeGreaterThan(300);
  });

  test("save the generated plan", async () => {
    await page.locator(".editor-title").fill(PLAN_TITLE);
    await page.getByRole("button", { name: /salvar plano/i }).click();
    await expect(page.locator(".status-inline")).toContainText(/salvo com sucesso/i);
  });

  test("list the saved plan", async () => {
    await page.goto("/planos", { waitUntil: "networkidle" });

    const planCard = page.locator(".plan-card", {
      has: page.getByRole("heading", { name: PLAN_TITLE, exact: true }),
    });

    await expect(planCard).toBeVisible();

    const editLink = planCard.getByRole("link", { name: /editar/i });
    const href = await editLink.getAttribute("href");
    createdPlanId = href?.split("/").pop() || null;
    expect(createdPlanId).toBeTruthy();
  });

  test("cleanup the saved plan", async () => {
    expect(createdPlanId).toBeTruthy();

    const token = await page.evaluate(() => window.localStorage.getItem("redocencia-token"));
    expect(token).toBeTruthy();

    const deleteResponse = await page.request.delete(`/api/plans/${createdPlanId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(deleteResponse.ok()).toBeTruthy();

    createdPlanId = null;
    await page.goto("/planos", { waitUntil: "networkidle" });
    await expect(page.getByRole("heading", { name: PLAN_TITLE, exact: true })).toHaveCount(0);
  });
});