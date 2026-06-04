import { expect, test } from "@playwright/test"
import { showAllResults } from "./utils/dataTable"
import { openPluginSources } from "./utils/media"
import { createUser } from "./utils/privateApi"
import { randomEmail, randomName, randomPassword } from "./utils/random"
import { logInUser } from "./utils/user"

test("Sources page is accessible and shows correct title", async ({ page }) => {
  await openPluginSources(page)
  await expect(
    page.getByRole("heading", { name: "Sources", exact: true }),
  ).toBeVisible()
})

test("Add Source button is visible", async ({ page }) => {
  await openPluginSources(page)
  await expect(page.getByRole("button", { name: "Add Source" })).toBeVisible()
})

test.describe("Sources management", () => {
  test.use({ storageState: { cookies: [], origins: [] } })
  let email: string
  const password = randomPassword()

  test.beforeAll(async () => {
    email = randomEmail()
    await createUser({ email, password })
  })

  test.beforeEach(async ({ page }) => {
    await logInUser(page, email, password)
    await openPluginSources(page)
  })

  test("Create a new source successfully", async ({ page }) => {
    const name = randomName("Source")

    await page.getByRole("button", { name: "Add Source" }).click()
    await page.getByLabel("Name").fill(name)
    await page.getByRole("button", { name: "Save" }).click()

    await expect(page.getByText("Source created successfully")).toBeVisible()
    await showAllResults(page)
    await expect(page.getByText(name)).toBeVisible()
  })

  test("Create source with only required fields", async ({ page }) => {
    await page.getByRole("button", { name: "Add Source" }).click()
    const key = await page.getByLabel("Key").inputValue()
    await page.getByRole("button", { name: "Save" }).click()

    await expect(page.getByText("Source created successfully")).toBeVisible()
    await showAllResults(page)
    await expect(page.getByText(`No Name (${key})`)).toBeVisible()
  })

  test("Cancel source creation", async ({ page }) => {
    await page.getByRole("button", { name: "Add Source" }).click()
    await page.getByLabel("Name").fill("Test Source")
    await page.getByRole("button", { name: "Cancel" }).click()

    await expect(page.getByRole("dialog")).not.toBeVisible()
  })

  test("Key is required", async ({ page }) => {
    await page.getByRole("button", { name: "Add Source" }).click()
    await page.getByLabel("Key").fill("")
    await page.getByLabel("Key").blur()

    await expect(page.getByText("Key is required")).toBeVisible()
  })

  test.describe("Edit and Delete", () => {
    let sourceName: string

    test.beforeEach(async ({ page }) => {
      sourceName = randomName("Source")

      await page.getByRole("button", { name: "Add Source" }).click()
      await page.getByLabel("Name").fill(sourceName)
      await page.getByRole("button", { name: "Save" }).click()
      await expect(page.getByText("Source created successfully")).toBeVisible()
      await expect(page.getByRole("dialog")).not.toBeVisible()
    })

    test("Edit a source successfully", async ({ page }) => {
      await showAllResults(page)
      const sourceRow = page.getByRole("row").filter({ hasText: sourceName })
      await sourceRow.getByRole("button", { name: "Edit Source" }).click()

      const updatedName = randomName("Source")
      await page.getByLabel("Name").fill(updatedName)
      await page.getByRole("button", { name: "Save" }).click()

      await expect(page.getByText("Source updated successfully")).toBeVisible()
      await expect(page.getByText(updatedName)).toBeVisible()
    })

    test("Delete a source successfully", async ({ page }) => {
      await showAllResults(page)
      const sourceRow = page.getByRole("row").filter({ hasText: sourceName })
      await sourceRow.getByRole("button", { name: "Delete Source" }).click()

      await page.getByRole("button", { name: "Delete" }).click()

      await expect(page.getByText("Source deleted successfully")).toBeVisible()
      await expect(page.getByText(sourceName)).not.toBeVisible()
    })
  })
})

test.describe("Sources empty state", () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test("Shows empty state message when no sources exist", async ({ page }) => {
    const email = randomEmail()
    const password = randomPassword()
    await createUser({ email, password })
    await logInUser(page, email, password)

    await openPluginSources(page)

    await expect(page.getByText("This plugin has no sources yet")).toBeVisible()
    await expect(page.getByText("Add a source to get started")).toBeVisible()
  })
})
