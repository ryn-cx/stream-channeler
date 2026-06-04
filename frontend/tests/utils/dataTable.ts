import type { Page } from "@playwright/test"

export async function showAllResults(page: Page) {
  const rowsPerPage = page.getByLabel("Rows per page")
  if (!(await rowsPerPage.isVisible().catch(() => false))) return
  await rowsPerPage.click()
  await page.getByRole("option", { name: "100000", exact: true }).click()
}
