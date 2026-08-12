// TODO: Validate
import { formatDuration } from "@/components/ChannelCommon/formatters"
import {
  CardMetaLines,
  type CardOverlayProps,
  CardSourceRow,
  CardTextArea,
} from "../components"

// TODO: Validate
export default function MovieCardOverlay({ episode }: CardOverlayProps) {
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
          {
            value: "Movie",
          },
        ]}
      />
    </CardTextArea>
  )
}
