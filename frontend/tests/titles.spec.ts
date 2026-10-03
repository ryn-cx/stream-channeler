// TODO: Validate
import { expect, test } from "@playwright/test"
import { showAllResults } from "./utils/dataTable"
import { openSourceTitles } from "./utils/media"
import { createUser } from "./utils/privateApi"
import { randomEmail, randomPassword, randomUsername } from "./utils/random"
import { logInUser } from "./utils/user"

test("Titles page is accessible and shows correct title", async ({ page }) => {
  await openSourceTitles(page)
  await expect(
    page.getByRole("heading", { name: "Titles", exact: true }),
  ).toBeVisible()
})

test("Add Title button is visible", async ({ page }) => {
  await openSourceTitles(page)
  await expect(page.getByRole("button", { name: "Add Title" })).toBeVisible()
})

test.describe("Titles management", () => {
  test.use({ storageState: { cookies: [], origins: [] } })
  let email: string
  const password = randomPassword()

  test.beforeAll(async () => {
    email = randomEmail()
    await createUser({ email, password })
  })

  test.beforeEach(async ({ page }) => {
    await logInUser(page, email, password)
    await openSourceTitles(page)
  })

  test("Create a new title successfully", async ({ page }) => {
    const name = randomUsername("Title")

    await page.getByRole("button", { name: "Add Title" }).click()
    await page.getByLabel("Name").fill(name)
    await page.getByRole("button", { name: "Save" }).click()

    await expect(page.getByText("Title created successfully")).toBeVisible()
    await showAllResults(page)
    await expect(page.getByText(name)).toBeVisible()
  })

  test("Create title with only required fields", async ({ page }) => {
    await page.getByRole("button", { name: "Add Title" }).click()
    const key = await page.getByLabel("Key").inputValue()
    await page.getByRole("button", { name: "Save" }).click()

    await expect(page.getByText("Title created successfully")).toBeVisible()
    await showAllResults(page)
    await expect(page.getByText(`No Name (${key})`)).toBeVisible()
  })

  test("Cancel title creation", async ({ page }) => {
    await page.getByRole("button", { name: "Add Title" }).click()
    await page.getByLabel("Name").fill("Test Title")
    await page.getByRole("button", { name: "Cancel" }).click()

    await expect(page.getByRole("dialog")).not.toBeVisible()
  })

  test("Key is required", async ({ page }) => {
    await page.getByRole("button", { name: "Add Title" }).click()
    await page.getByLabel("Key").fill("")
    await page.getByLabel("Key").blur()

    await expect(page.getByText("Key is required")).toBeVisible()
  })

  test.describe("Edit and Delete", () => {
    let titleName: string

    test.beforeEach(async ({ page }) => {
      titleName = randomUsername("Title")

      await page.getByRole("button", { name: "Add Title" }).click()
      await page.getByLabel("Name").fill(titleName)
      await page.getByRole("button", { name: "Save" }).click()
      await expect(page.getByText("Title created successfully")).toBeVisible()
      await expect(page.getByRole("dialog")).not.toBeVisible()
    })

    test("Edit a title successfully", async ({ page }) => {
      await showAllResults(page)
      const titleRow = page.getByRole("row").filter({ hasText: titleName })
      await titleRow.getByRole("button", { name: "Edit Title" }).click()

      const updatedName = randomUsername("Title")
      await page.getByLabel("Name").fill(updatedName)
      await page.getByRole("button", { name: "Save" }).click()

      await expect(page.getByText("Title updated successfully")).toBeVisible()
      await expect(page.getByText(updatedName)).toBeVisible()
    })

    test("Delete a title successfully", async ({ page }) => {
      await showAllResults(page)
      const titleRow = page.getByRole("row").filter({ hasText: titleName })
      await titleRow.getByRole("button", { name: "Delete Title" }).click()

      await page.getByRole("button", { name: "Delete" }).click()

      await expect(page.getByText("Title deleted successfully")).toBeVisible()
      await expect(page.getByText(titleName)).not.toBeVisible()
    })
  })
})

test.describe("Titles empty state", () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test("Titles empty state message when no titles exist", async ({ page }) => {
    const email = randomEmail()
    const password = randomPassword()
    await createUser({ email, password })
    await logInUser(page, email, password)

    await openSourceTitles(page)

    await expect(page.getByText("This source has no titles yet")).toBeVisible()
    await expect(page.getByText("Add a title to get started")).toBeVisible()
  })
})
