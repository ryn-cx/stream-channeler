// TODO: Validate
import type { EpisodeWithDetails } from "../../columns"

interface CardOverlayProps {
  episode: EpisodeWithDetails
  formatDuration: (seconds: number) => string
}

export default function TVShowCardOverlay({
  episode,
  formatDuration,
}: CardOverlayProps) {
  const releaseDate = episode.air_date || episode.release_date

  return (
    // -mt-6 - Negative margin to reduce the size between the image and the text.
    <div className="-mt-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 flex-1">
          {episode.source.favicon_url && (
            <img
              src={episode.source.favicon_url}
              alt={episode.source.name ?? undefined}
              className="size-6"
            />
          )}
          <span className="font-bold text-sm">{episode.show.name}</span>
        </div>
        <div className="flex flex-col items-end gap-0">
          {releaseDate && (
            <span className="text-xs text-muted-foreground">
              {new Date(releaseDate).toLocaleDateString()}
            </span>
          )}
          {episode.duration && (
            <span className="text-xs text-muted-foreground">
              {formatDuration(episode.duration)}
            </span>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-0">
        <span className="text-sm text-muted-foreground truncate">
          Season {episode.season.season_number}
          {episode.season.name ? `: ${episode.season.name}` : ""}
        </span>
        <span className="text-sm text-muted-foreground truncate">
          Episode {episode.episode_number}
          {episode.name ? `: ${episode.name}` : ""}
        </span>
      </div>
    </div>
  )
}
