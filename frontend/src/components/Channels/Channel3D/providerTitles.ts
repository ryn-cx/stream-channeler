// TODO: Validate
import { VideoStoreService } from "@/client"

// TODO: Validate
export const fetchProviderTitles = async (
  watchProviderId: string,
  region: string,
) => {
  const page = await VideoStoreService.getProviderTitles({
    watchProviderId,
    region,
  })
  return page.titles.map((title) => ({
    id: title.id,
    name: title.name || "Untitled",
    year: title.year,
    tmdbScore: title.tmdb_score,
    tmdbPopularity: title.tmdb_popularity,
    imdbScore: title.imdb_score,
    imdbPopularity: title.imdb_popularity,
    mediaType: title.media_type,
    originalLanguage: title.original_language,
    languages: title.languages,
    imageUrl: title.thumbnail_url,
    isPoster: title.is_poster,
    genres: title.genres,
    episodeCount: title.episode_count,
    seasonCount: title.season_count,
  }))
}
