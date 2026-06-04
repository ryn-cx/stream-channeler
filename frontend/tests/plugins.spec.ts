import { expect, test } from "@playwright/test"
import { showAllResults } from "./utils/dataTable"
import { createUser } from "./utils/privateApi"
import { randomEmail, randomName, randomPassword } from "./utils/random"
import { logInUser } from "./utils/user"

test("Plugins page is accessible and shows correct title", async ({ page }) => {
  await page.goto("/plugins")
  await expect(page.getByRole("heading", { name: "Plugins" })).toBeVisible()
})

test("Add Plugin button is visible", async ({ page }) => {
  await page.goto("/plugins")
  await expect(page.getByRole("button", { name: "Add Plugin" })).toBeVisible()
})

test.describe("Plugins management", () => {
  test.use({ storageState: { cookies: [], origins: [] } })
  let email: string
  const password = randomPassword()

  test.beforeAll(async () => {
    email = randomEmail()
    await createUser({ email, password })
  })

  test.beforeEach(async ({ page }) => {
    await logInUser(page, email, password)
    await page.goto("/plugins")
  })

  test("Create a new plugin successfully", async ({ page }) => {
    const name = randomName("Plugin")

    await page.getByRole("button", { name: "Add Plugin" }).click()
    await page.getByLabel("Name").fill(name)
    await page.getByRole("button", { name: "Save" }).click()

    await expect(page.getByText("Plugin created successfully")).toBeVisible()
    await showAllResults(page)
    await expect(page.getByText(name)).toBeVisible()
  })

  test("Create plugin with only required fields", async ({ page }) => {
    await page.getByRole("button", { name: "Add Plugin" }).click()
    const key = await page.getByLabel("Key").inputValue()
    await page.getByRole("button", { name: "Save" }).click()

    await expect(page.getByText("Plugin created successfully")).toBeVisible()
    await showAllResults(page)
    await expect(page.getByText(`No Name (${key})`)).toBeVisible()
  })

  test("Cancel plugin creation", async ({ page }) => {
    await page.getByRole("button", { name: "Add Plugin" }).click()
    await page.getByLabel("Name").fill("Test Plugin")
    await page.getByRole("button", { name: "Cancel" }).click()

    await expect(page.getByRole("dialog")).not.toBeVisible()
  })

  test("Key is required", async ({ page }) => {
    await page.getByRole("button", { name: "Add Plugin" }).click()
    await page.getByLabel("Key").fill("")
    await page.getByLabel("Key").blur()

    await expect(page.getByText("Key is required")).toBeVisible()
  })

  test.describe("Edit and Delete", () => {
    let pluginName: string

    test.beforeEach(async ({ page }) => {
      pluginName = randomName("Plugin")

      await page.getByRole("button", { name: "Add Plugin" }).click()
      await page.getByLabel("Name").fill(pluginName)
      await page.getByRole("button", { name: "Save" }).click()
      await expect(page.getByText("Plugin created successfully")).toBeVisible()
      await expect(page.getByRole("dialog")).not.toBeVisible()
    })

    test("Edit a plugin successfully", async ({ page }) => {
      await showAllResults(page)
      const pluginRow = page.getByRole("row").filter({ hasText: pluginName })
      await pluginRow.getByRole("button", { name: "Edit plugin" }).click()

      const updatedName = randomName("Plugin")
      await page.getByLabel("Name").fill(updatedName)
      await page.getByRole("button", { name: "Save" }).click()

      await expect(page.getByText("Plugin updated successfully")).toBeVisible()
      await expect(page.getByText(updatedName)).toBeVisible()
    })

    test("Delete a plugin successfully", async ({ page }) => {
      await showAllResults(page)
      const pluginRow = page.getByRole("row").filter({ hasText: pluginName })
      await pluginRow.getByRole("button", { name: "Delete plugin" }).click()

      await page.getByRole("button", { name: "Delete" }).click()

      await expect(page.getByText("Plugin deleted successfully")).toBeVisible()
      await expect(page.getByText(pluginName)).not.toBeVisible()
    })
  })
})

test.describe("Plugins empty state", () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test("Shows empty state message when no plugins exist", async ({ page }) => {
    const email = randomEmail()
    const password = randomPassword()
    await createUser({ email, password })
    await logInUser(page, email, password)

    await page.goto("/plugins")

    await expect(page.getByText("You don't have any plugins yet")).toBeVisible()
    await expect(page.getByText("Add a plugin to get started")).toBeVisible()
  })
})
