// TODO: Validate
import { formatDuration } from "@/components/ChannelCommon/formatters"
import {
  CardMetaLines,
  type CardOverlayProps,
  CardSourceRow,
  CardTextArea,
} from "../components"

// TODO: Validate
export default function YouTubeCardOverlay({ episode }: CardOverlayProps) {
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
          { label: "Playlist:", value: episode.season.name },
          {
            label: "Video:",
            value: episode.name,
            valueClassName: "font-bold",
          },
        ]}
      />
    </CardTextArea>
  )
}
