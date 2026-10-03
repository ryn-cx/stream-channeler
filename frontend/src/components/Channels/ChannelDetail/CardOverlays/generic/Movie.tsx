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
export default function MovieCardOverlay({ episode }: CardOverlayProps) {
  const isLinked = episode.tmdb_episode_id !== episode.id

  const sourceBlock = {
    name: episode.source_title_name ?? episode.title.name,
    details: [
      formatAirDate(episode.source_air_date),
      formatDuration(episode.source_duration),
    ],
    lines: [{ value: "Movie" }],
  }

  const tmdbBlock = {
    name: episode.tmdb_title_name,
    details: [
      formatAirDate(episode.air_date),
      formatDuration(episode.duration),
    ],
    lines: [{ value: "Movie" }],
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
