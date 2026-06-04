import { expect, test } from "@playwright/test"
import { showAllResults } from "./utils/dataTable"
import { openSourceShows } from "./utils/media"
import { createUser } from "./utils/privateApi"
import { randomEmail, randomName, randomPassword } from "./utils/random"
import { logInUser } from "./utils/user"

test("Shows page is accessible and shows correct title", async ({ page }) => {
  await openSourceShows(page)
  await expect(
    page.getByRole("heading", { name: "Shows", exact: true }),
  ).toBeVisible()
})

test("Add Show button is visible", async ({ page }) => {
  await openSourceShows(page)
  await expect(page.getByRole("button", { name: "Add Show" })).toBeVisible()
})

test.describe("Shows management", () => {
  test.use({ storageState: { cookies: [], origins: [] } })
  let email: string
  const password = randomPassword()

  test.beforeAll(async () => {
    email = randomEmail()
    await createUser({ email, password })
  })

  test.beforeEach(async ({ page }) => {
    await logInUser(page, email, password)
    await openSourceShows(page)
  })

  test("Create a new show successfully", async ({ page }) => {
    const name = randomName("Show")

    await page.getByRole("button", { name: "Add Show" }).click()
    await page.getByLabel("Name").fill(name)
    await page.getByRole("button", { name: "Save" }).click()

    await expect(page.getByText("Show created successfully")).toBeVisible()
    await showAllResults(page)
    await expect(page.getByText(name)).toBeVisible()
  })

  test("Create show with only required fields", async ({ page }) => {
    await page.getByRole("button", { name: "Add Show" }).click()
    const key = await page.getByLabel("Key").inputValue()
    await page.getByRole("button", { name: "Save" }).click()

    await expect(page.getByText("Show created successfully")).toBeVisible()
    await showAllResults(page)
    await expect(page.getByText(`No Name (${key})`)).toBeVisible()
  })

  test("Cancel show creation", async ({ page }) => {
    await page.getByRole("button", { name: "Add Show" }).click()
    await page.getByLabel("Name").fill("Test Show")
    await page.getByRole("button", { name: "Cancel" }).click()

    await expect(page.getByRole("dialog")).not.toBeVisible()
  })

  test("Key is required", async ({ page }) => {
    await page.getByRole("button", { name: "Add Show" }).click()
    await page.getByLabel("Key").fill("")
    await page.getByLabel("Key").blur()

    await expect(page.getByText("Key is required")).toBeVisible()
  })

  test.describe("Edit and Delete", () => {
    let showName: string

    test.beforeEach(async ({ page }) => {
      showName = randomName("Show")

      await page.getByRole("button", { name: "Add Show" }).click()
      await page.getByLabel("Name").fill(showName)
      await page.getByRole("button", { name: "Save" }).click()
      await expect(page.getByText("Show created successfully")).toBeVisible()
      await expect(page.getByRole("dialog")).not.toBeVisible()
    })

    test("Edit a show successfully", async ({ page }) => {
      await showAllResults(page)
      const showRow = page.getByRole("row").filter({ hasText: showName })
      await showRow.getByRole("button", { name: "Edit Show" }).click()

      const updatedName = randomName("Show")
      await page.getByLabel("Name").fill(updatedName)
      await page.getByRole("button", { name: "Save" }).click()

      await expect(page.getByText("Show updated successfully")).toBeVisible()
      await expect(page.getByText(updatedName)).toBeVisible()
    })

    test("Delete a show successfully", async ({ page }) => {
      await showAllResults(page)
      const showRow = page.getByRole("row").filter({ hasText: showName })
      await showRow.getByRole("button", { name: "Delete Show" }).click()

      await page.getByRole("button", { name: "Delete" }).click()

      await expect(page.getByText("Show deleted successfully")).toBeVisible()
      await expect(page.getByText(showName)).not.toBeVisible()
    })
  })
})

test.describe("Shows empty state", () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test("Shows empty state message when no shows exist", async ({ page }) => {
    const email = randomEmail()
    const password = randomPassword()
    await createUser({ email, password })
    await logInUser(page, email, password)

    await openSourceShows(page)

    await expect(page.getByText("This source has no shows yet")).toBeVisible()
    await expect(page.getByText("Add a show to get started")).toBeVisible()
  })
})
