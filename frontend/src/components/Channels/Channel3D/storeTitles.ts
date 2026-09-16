// TODO: Validate
import { ChannelsService, type TitlePublic } from "@/client"
import type { StoreTitle } from "./caseTexture"

// TODO: Validate
export const fetchStoreTitles = async (channelId: string) => {
  const first = await ChannelsService.getChannelTitles({
    channelId,
    limit: 100,
  })
  const pages = [first]
  const offsets: number[] = []
  for (let offset = 100; offset < (first.total ?? 0); offset += 100) {
    offsets.push(offset)
  }
  while (offsets.length > 0) {
    const batch = offsets.splice(0, 6)
    pages.push(
      ...(await Promise.all(
        batch.map((offset) =>
          ChannelsService.getChannelTitles({ channelId, limit: 100, offset }),
        ),
      )),
    )
  }

  const shelved = new Map<string, StoreTitle>()
  for (const page of pages) {
    for (const title of page.titles ?? []) {
      const key = title.tmdb_title_id ?? title.id
      const stats = page.stats?.[key]
      const artwork = pickArtwork(page.tmdb_titles?.[key], title)
      const existing = shelved.get(key)
      if (existing) {
        existing.url ??= title.url ?? null
        existing.imageUrl ??= artwork
        continue
      }
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
  }

  return [...shelved.values()].sort((left, right) =>
    left.name.localeCompare(right.name),
  )
}

// TODO: Validate
const pickArtwork = (
  linkedTitle: TitlePublic | undefined,
  title: TitlePublic,
) => linkedTitle?.thumbnail_url || title.thumbnail_url || null
