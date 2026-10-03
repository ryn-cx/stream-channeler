// TODO: Validate
import { formatDuration } from "@/components/ChannelCommon/formatters"
import {
  CardEpisodeBlock,
  type CardOverlayProps,
  CardSourceSection,
  CardTextArea,
} from "../components"

// TODO: Validate
function formatAirDate(airDate: string | null | undefined): string | null {
  return airDate ? new Date(airDate).toLocaleDateString() : null
}

// TODO: Validate
export default function YouTubeCardOverlay({ episode }: CardOverlayProps) {
  const isLinked = episode.tmdb_episode_id !== episode.id

  const sourceBlock = {
    name: episode.source_title_name ?? episode.title.name,
    details: [
      formatAirDate(episode.source_air_date),
      formatDuration(episode.source_duration),
    ],
    lines: [
      {
        label: "Playlist:",
        value: episode.source_season_name ?? episode.season.name,
      },
      {
        label: "Video:",
        value: episode.source_name,
        valueClassName: "font-bold",
      },
    ],
  }

  const tmdbBlock = {
    name: episode.tmdb_title_name,
    details: [
      formatAirDate(episode.air_date),
      formatDuration(episode.duration),
    ],
    lines: [
      { label: "Season:", value: episode.tmdb_season_name },
      {
        label: "Episode:",
        value: episode.name,
        valueClassName: "font-bold",
      },
    ],
  }

  return (
    <CardTextArea>
      <CardEpisodeBlock
        iconUrl={isLinked ? "/tmdb.svg" : episode.source.favicon_url}
        iconAlt={isLinked ? "TMDB" : episode.source.key}
        {...(isLinked ? tmdbBlock : sourceBlock)}
      />
      {isLinked && (
        <CardSourceSection label={`${episode.source.key} Episode Information`}>
          <CardEpisodeBlock iconAlt={episode.source.key} {...sourceBlock} />
        </CardSourceSection>
      )}
    </CardTextArea>
  )
}
