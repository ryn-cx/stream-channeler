// TODO: Validate
import { VideoStoreService } from "@/client"
import type { StoreTitle } from "./caseTexture"

export const SOURCE_TITLE_PAGE = 200

// TODO: Validate
const shrinkArtwork = (url: string | null) =>
  url?.replace(
    /^(https?:\/\/image\.tmdb\.org\/t\/p\/)(w\d+|h\d+|original)\//,
    "$1w185/",
  ) ?? null

// TODO: Validate
export const fetchSourceTitlePage = async (
  sourceId: string,
  offset: number,
) => {
  const page = await VideoStoreService.getStoreTitles({
    sourceId,
    limit: SOURCE_TITLE_PAGE,
    offset,
  })
  const titles: StoreTitle[] = page.titles.map((title) => ({
    id: title.id,
    name: title.name || "Untitled",
    year: title.year,
    imageUrl: shrinkArtwork(title.poster_thumbnail_url || title.thumbnail_url),
    isPoster: Boolean(title.poster_thumbnail_url),
    genres: title.genres,
    fullImageUrl: title.poster_url || title.image_url,
    backImageUrl: title.image_url,
    description: title.description,
    episodeCount: title.episode_count,
    seasonCount: title.season_count,
    url: title.url,
  }))
  return { titles, total: page.total }
}
