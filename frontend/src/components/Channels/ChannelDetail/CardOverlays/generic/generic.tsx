// TODO: Validate
import { formatDuration } from "@/components/ChannelCommon/formatters"
import {
  CardMetaLines,
  type CardOverlayProps,
  CardSourceRow,
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
export default function TVShowCardOverlay({ episode }: CardOverlayProps) {
  const airDate = episode.air_date

  return (
    <CardTextArea>
      <CardSourceRow
        episode={episode}
        details={[
          airDate ? new Date(airDate).toLocaleDateString() : null,
          formatDuration(episode.duration),
        ]}
      />
      <CardMetaLines
        lines={[
          formatNumberedLine(
            "Season",
            episode.season.season_number,
            episode.season.name,
          ),
          {
            ...formatNumberedLine(
              "Episode",
              episode.episode_number,
              episode.name,
            ),
            valueClassName: "font-bold",
          },
        ]}
      />
    </CardTextArea>
  )
}
