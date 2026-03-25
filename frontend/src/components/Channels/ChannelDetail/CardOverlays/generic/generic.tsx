import { formatDuration } from "../../EpisodeCards"
import {
  CardMetaLines,
  type CardOverlayProps,
  CardSourceRow,
  CardTextArea,
} from "../components"

function formatNumberedLine(
  label: string,
  number: number | null | undefined,
  name: string | null | undefined,
): { label?: string; value: string | null } {
  if (number && name) return { label, value: `${number} ∙ ${name}` }
  if (name) return { label, value: name }
  if (number) return { value: `${label} ${number}` }
  return { value: null }
}

export default function TVShowCardOverlay({ episode }: CardOverlayProps) {
  const releaseDate = episode.air_date || episode.release_date

  return (
    <CardTextArea>
      <CardSourceRow
        episode={episode}
        details={[
          releaseDate ? new Date(releaseDate).toLocaleDateString() : null,
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
