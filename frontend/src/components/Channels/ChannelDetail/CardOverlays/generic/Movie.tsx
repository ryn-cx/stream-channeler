// TODO: Validate
import { formatDuration } from "../../EpisodeCards"
import {
  CardMetaLines,
  type CardOverlayProps,
  CardSourceRow,
  CardTextArea,
} from "../components"

export default function MovieCardOverlay({ episode }: CardOverlayProps) {
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
          {
            value: "Movie",
          },
        ]}
      />
    </CardTextArea>
  )
}
