// TODO: Validate
import { expect, test } from "@playwright/test"
import { showAllResults } from "./utils/dataTable"
import { openSeasonEpisodes } from "./utils/media"
import { createUser } from "./utils/privateApi"
import { randomEmail, randomUsername, randomPassword } from "./utils/random"
import { logInUser } from "./utils/user"

test("Episodes page is accessible and shows correct title", async ({
  page,
}) => {
  await openSeasonEpisodes(page)
  await expect(
    page.getByRole("heading", { name: "Episodes", exact: true }),
  ).toBeVisible()
})

test("Add Episode button is visible", async ({ page }) => {
  await openSeasonEpisodes(page)
  await expect(page.getByRole("button", { name: "Add Episode" })).toBeVisible()
})

test.describe("Episodes management", () => {
  test.use({ storageState: { cookies: [], origins: [] } })
  let email: string
  const password = randomPassword()

  test.beforeAll(async () => {
    email = randomEmail()
    await createUser({ email, password })
  })

  test.beforeEach(async ({ page }) => {
    await logInUser(page, email, password)
    await openSeasonEpisodes(page)
  })

  test("Create a new episode successfully", async ({ page }) => {
    const name = randomUsername("Episode")

    await page.getByRole("button", { name: "Add Episode" }).click()
    await page.getByLabel("Name").fill(name)
    await page.getByRole("button", { name: "Save" }).click()

    await expect(page.getByText("Episode created successfully")).toBeVisible()
    await showAllResults(page)
    await expect(page.getByText(name)).toBeVisible()
  })

  test("Create episode with only required fields", async ({ page }) => {
    await page.getByRole("button", { name: "Add Episode" }).click()
    const key = await page.getByLabel("Key").inputValue()
    await page.getByRole("button", { name: "Save" }).click()

    await expect(page.getByText("Episode created successfully")).toBeVisible()
    await showAllResults(page)
    await expect(page.getByText(`No Name (${key})`)).toBeVisible()
  })

  test("Cancel episode creation", async ({ page }) => {
    await page.getByRole("button", { name: "Add Episode" }).click()
    await page.getByLabel("Name").fill("Test Episode")
    await page.getByRole("button", { name: "Cancel" }).click()

    await expect(page.getByRole("dialog")).not.toBeVisible()
  })

  test("Key is required", async ({ page }) => {
    await page.getByRole("button", { name: "Add Episode" }).click()
    await page.getByLabel("Key").fill("")
    await page.getByLabel("Key").blur()

    await expect(page.getByText("Key is required")).toBeVisible()
  })

  test.describe("Edit and Delete", () => {
    let episodeName: string

    test.beforeEach(async ({ page }) => {
      episodeName = randomUsername("Episode")

      await page.getByRole("button", { name: "Add Episode" }).click()
      await page.getByLabel("Name").fill(episodeName)
      await page.getByRole("button", { name: "Save" }).click()
      await expect(page.getByText("Episode created successfully")).toBeVisible()
      await expect(page.getByRole("dialog")).not.toBeVisible()
    })

    test("Edit an episode successfully", async ({ page }) => {
      await showAllResults(page)
      const episodeRow = page.getByRole("row").filter({ hasText: episodeName })
      await episodeRow.getByRole("button", { name: "Edit Episode" }).click()

      const updatedName = randomUsername("Episode")
      await page.getByLabel("Name").fill(updatedName)
      await page.getByRole("button", { name: "Save" }).click()

      await expect(page.getByText("Episode updated successfully")).toBeVisible()
      await expect(page.getByText(updatedName)).toBeVisible()
    })

    test("Delete an episode successfully", async ({ page }) => {
      await showAllResults(page)
      const episodeRow = page.getByRole("row").filter({ hasText: episodeName })
      await episodeRow.getByRole("button", { name: "Delete Episode" }).click()

      await page.getByRole("button", { name: "Delete" }).click()

      await expect(page.getByText("Episode deleted successfully")).toBeVisible()
      await expect(page.getByText(episodeName)).not.toBeVisible()
    })
  })
})

test.describe("Episodes empty state", () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test("Shows empty state message when no episodes exist", async ({ page }) => {
    const email = randomEmail()
    const password = randomPassword()
    await createUser({ email, password })
    await logInUser(page, email, password)

    await openSeasonEpisodes(page)

    await expect(
      page.getByText("This season has no episodes yet"),
    ).toBeVisible()
    await expect(page.getByText("Add an episode to get started")).toBeVisible()
  })
})
