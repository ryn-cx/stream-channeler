import { expect, test } from "@playwright/test"
import { showAllResults } from "./utils/dataTable"
import { openShowSeasons } from "./utils/media"
import { createUser } from "./utils/privateApi"
import { randomEmail, randomName, randomPassword } from "./utils/random"
import { logInUser } from "./utils/user"

test("Seasons page is accessible and shows correct title", async ({ page }) => {
  await openShowSeasons(page)
  await expect(
    page.getByRole("heading", { name: "Seasons", exact: true }),
  ).toBeVisible()
})

test("Add Season button is visible", async ({ page }) => {
  await openShowSeasons(page)
  await expect(page.getByRole("button", { name: "Add Season" })).toBeVisible()
})

test.describe("Seasons management", () => {
  test.use({ storageState: { cookies: [], origins: [] } })
  let email: string
  const password = randomPassword()

  test.beforeAll(async () => {
    email = randomEmail()
    await createUser({ email, password })
  })

  test.beforeEach(async ({ page }) => {
    await logInUser(page, email, password)
    await openShowSeasons(page)
  })

  test("Create a new season successfully", async ({ page }) => {
    const name = randomName("Season")

    await page.getByRole("button", { name: "Add Season" }).click()
    await page.getByLabel("Name").fill(name)
    await page.getByRole("button", { name: "Save" }).click()

    await expect(page.getByText("Season created successfully")).toBeVisible()
    await showAllResults(page)
    await expect(page.getByText(name)).toBeVisible()
  })

  test("Create season with only required fields", async ({ page }) => {
    await page.getByRole("button", { name: "Add Season" }).click()
    const key = await page.getByLabel("Key").inputValue()
    await page.getByRole("button", { name: "Save" }).click()

    await expect(page.getByText("Season created successfully")).toBeVisible()
    await showAllResults(page)
    await expect(page.getByText(`No Name (${key})`)).toBeVisible()
  })

  test("Cancel season creation", async ({ page }) => {
    await page.getByRole("button", { name: "Add Season" }).click()
    await page.getByLabel("Name").fill("Test Season")
    await page.getByRole("button", { name: "Cancel" }).click()

    await expect(page.getByRole("dialog")).not.toBeVisible()
  })

  test("Key is required", async ({ page }) => {
    await page.getByRole("button", { name: "Add Season" }).click()
    await page.getByLabel("Key").fill("")
    await page.getByLabel("Key").blur()

    await expect(page.getByText("Key is required")).toBeVisible()
  })

  test.describe("Edit and Delete", () => {
    let seasonName: string

    test.beforeEach(async ({ page }) => {
      seasonName = randomName("Season")

      await page.getByRole("button", { name: "Add Season" }).click()
      await page.getByLabel("Name").fill(seasonName)
      await page.getByRole("button", { name: "Save" }).click()
      await expect(page.getByText("Season created successfully")).toBeVisible()
      await expect(page.getByRole("dialog")).not.toBeVisible()
    })

    test("Edit a season successfully", async ({ page }) => {
      await showAllResults(page)
      const seasonRow = page.getByRole("row").filter({ hasText: seasonName })
      await seasonRow.getByRole("button", { name: "Edit Season" }).click()

      const updatedName = randomName("Season")
      await page.getByLabel("Name").fill(updatedName)
      await page.getByRole("button", { name: "Save" }).click()

      await expect(page.getByText("Season updated successfully")).toBeVisible()
      await expect(page.getByText(updatedName)).toBeVisible()
    })

    test("Delete a season successfully", async ({ page }) => {
      await showAllResults(page)
      const seasonRow = page.getByRole("row").filter({ hasText: seasonName })
      await seasonRow.getByRole("button", { name: "Delete Season" }).click()

      await page.getByRole("button", { name: "Delete" }).click()

      await expect(page.getByText("Season deleted successfully")).toBeVisible()
      await expect(page.getByText(seasonName)).not.toBeVisible()
    })
  })
})

test.describe("Seasons empty state", () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test("Shows empty state message when no seasons exist", async ({ page }) => {
    const email = randomEmail()
    const password = randomPassword()
    await createUser({ email, password })
    await logInUser(page, email, password)

    await openShowSeasons(page)

    await expect(page.getByText("This show has no seasons yet")).toBeVisible()
    await expect(page.getByText("Add a season to get started")).toBeVisible()
  })
})
