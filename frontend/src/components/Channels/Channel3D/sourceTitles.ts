// TODO: Validate
import { VideoStoreService } from "@/client"

// TODO: Validate
const shrinkArtwork = (url: string | null) =>
  url?.replace(
    /^(https?:\/\/image\.tmdb\.org\/t\/p\/)(w\d+|h\d+|original)\//,
    "$1w185/",
  ) ?? null

// TODO: Validate
export const fetchSourceTitles = async (sourceId: string) => {
  const page = await VideoStoreService.getStoreTitles({ sourceId })
  return page.titles.map((title) => ({
    id: title.id,
    name: title.name || "Untitled",
    year: title.year,
    score: title.score,
    popularity: title.popularity,
    mediaType: title.media_type,
    originalLanguage: title.original_language,
    languages: title.languages,
    imageUrl: shrinkArtwork(title.thumbnail_url),
    isPoster: title.is_poster,
    genres: title.genres.map((genre) => ({
      source: genre.plugin_name,
      name: genre.name,
    })),
    episodeCount: title.episode_count,
    seasonCount: title.season_count,
  }))
}
