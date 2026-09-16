// TODO: Validate
import { ChannelsService, type TitlePublic } from "@/client"
import type { StoreTitle } from "./caseTexture"

export const TITLE_PAGE = 100

// TODO: Validate
const pickArtwork = (
  linkedTitle: TitlePublic | undefined,
  title: TitlePublic,
) => linkedTitle?.thumbnail_url || title.thumbnail_url || null

// TODO: Validate
const shrinkArtwork = (url: string | null) =>
  url?.replace(
    /^(https?:\/\/image\.tmdb\.org\/t\/p\/)(w\d+|h\d+|original)\//,
    "$1w185/",
  ) ?? null

// TODO: Validate
export const fetchTitlePage = async (channelId: string, offset: number) => {
  const page = await ChannelsService.getChannelTitles({
    channelId,
    limit: TITLE_PAGE,
    offset,
  })

  const shelved = new Map<string, StoreTitle>()
  for (const title of page.titles ?? []) {
    const key = title.tmdb_title_id ?? title.id
    const artwork = shrinkArtwork(pickArtwork(page.tmdb_titles?.[key], title))
    const existing = shelved.get(key)
    if (existing) {
      existing.url ??= title.url ?? null
      existing.imageUrl ??= artwork
      continue
    }
    const stats = page.stats?.[key]
    shelved.set(key, {
      id: key,
      name: title.name || "Untitled",
      year: title.year ?? null,
      imageUrl: artwork,
      episodeCount: stats?.episode_count ?? 0,
      seasonCount: stats?.season_count ?? 0,
      url: title.url ?? null,
    })
  }

  const titles = [...shelved.values()].sort((left, right) =>
    left.name.localeCompare(right.name),
  )
  return { titles, total: page.total ?? titles.length }
}
