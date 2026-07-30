// TODO: Validate
import { expect, type Page } from "@playwright/test"
import { showAllResults } from "./dataTable"
import { randomUsername } from "./random"

/**
 * Helpers that build the parent chain through the UI. Sources live under a
 * plugin, shows under a source, seasons under a show and episodes under a
 * season, so each level's tests first need the level above it to exist and be
 * open. Every helper leaves the page on the freshly created parent's (empty)
 * child list.
 */

async function createAndOpen(
  page: Page,
  {
    addButton,
    name,
    createdToast,
    heading,
  }: {
    addButton: string
    name: string
    createdToast: string
    heading: string
  },
) {
  await page.getByRole("button", { name: addButton }).click()
  await page.getByLabel("Name").fill(name)
  await page.getByRole("button", { name: "Save" }).click()
  await expect(page.getByText(createdToast)).toBeVisible()
  await showAllResults(page)
  await page.getByRole("link", { name }).click()
  await expect(
    page.getByRole("heading", { name: heading, exact: true }),
  ).toBeVisible()
}

/** Create a plugin and open its Sources page. */
export async function openPluginSources(page: Page) {
  await page.goto("/plugins")
  await createAndOpen(page, {
    addButton: "Add Plugin",
    name: randomUsername("Plugin"),
    createdToast: "Plugin created successfully",
    heading: "Sources",
  })
}

/** Create a plugin and source, then open the source's Shows page. */
export async function openSourceShows(page: Page) {
  await openPluginSources(page)
  await createAndOpen(page, {
    addButton: "Add Source",
    name: randomUsername("Source"),
    createdToast: "Source created successfully",
    heading: "Shows",
  })
}

/** Create the plugin/source/show chain, then open the show's Seasons page. */
export async function openShowSeasons(page: Page) {
  await openSourceShows(page)
  await createAndOpen(page, {
    addButton: "Add Show",
    name: randomUsername("Show"),
    createdToast: "Show created successfully",
    heading: "Seasons",
  })
}

/** Create the full chain down to a season, then open its Episodes page. */
export async function openSeasonEpisodes(page: Page) {
  await openShowSeasons(page)
  await createAndOpen(page, {
    addButton: "Add Season",
    name: randomUsername("Season"),
    createdToast: "Season created successfully",
    heading: "Episodes",
  })
}
