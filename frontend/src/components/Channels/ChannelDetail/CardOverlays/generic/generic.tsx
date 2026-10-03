// TODO: Validate
import { EpisodeTitle } from "@/components/ChannelCommon/EpisodeTitle"
import { formatDuration } from "@/components/ChannelCommon/formatters"
import {
  CardEpisodeBlock,
  type CardOverlayProps,
  CardSourceSection,
  CardTextArea,
} from "../components"

// TODO: Validate
function nameMatchesNumber(
  label: string,
  number: number,
  name: string,
): boolean {
  const normalized = name.trim().toLowerCase()
  return normalized === `${label.toLowerCase()} ${number}`
}

// TODO: Validate
function formatNumberedLine(
  label: string,
  number: number | null | undefined,
  name: string | null | undefined,
): { label?: string; value: string | null } {
  // Season 0 is TMDB's specials, so a number is only missing when it is nullish.
  if (number == null) return name ? { label, value: name } : { value: null }
  if (!name) return { value: `${label} ${number}` }
  if (nameMatchesNumber(label, number, name)) return { value: name }
  return { label, value: `${number} ∙ ${name}` }
}

// TODO: Validate
function formatAirDate(airDate: string | null | undefined): string | null {
  return airDate ? new Date(airDate).toLocaleDateString() : null
}

// TODO: Validate
export default function TVShowCardOverlay({ episode }: CardOverlayProps) {
  const isLinked = episode.tmdb_episode_id !== episode.id

  const sourceBlock = {
    name: episode.source_title_name ?? episode.title.name,
    details: [
      formatAirDate(episode.source_air_date),
      formatDuration(episode.source_duration),
    ],
    lines: [
      formatNumberedLine(
        "Season",
        episode.source_season_number,
        episode.source_season_name,
      ),
      {
        value: (
          <EpisodeTitle
            name={episode.source_name}
            episodeNumber={episode.source_episode_number}
          />
        ),
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
      formatNumberedLine(
        "Season",
        episode.tmdb_season_number,
        episode.tmdb_season_name,
      ),
      {
        value: (
          <EpisodeTitle
            name={episode.name}
            episodeNumber={episode.tmdb_episode_number}
          />
        ),
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
