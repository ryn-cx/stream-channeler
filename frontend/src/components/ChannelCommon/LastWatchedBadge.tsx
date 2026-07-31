// TODO: Validate
import { Badge } from "@/components/ui/badge"

interface LastWatchedBadgeProps {
  episode: {
    watch_date?: string | null
    verified?: boolean | null
  }
}

/** "Last Watched" marker shared by the episode cards and the hero billboard. */
export function LastWatchedBadge({ episode }: LastWatchedBadgeProps) {
  if (!episode.watch_date) return null

  const formattedDate = new Date(episode.watch_date).toLocaleDateString()
  return (
    <Badge variant={episode.verified ? "default" : "secondary"}>
      {episode.verified
        ? `Last Watched - ${formattedDate}`
        : `Last Watched - ${formattedDate} (Not Verified)`}
    </Badge>
  )
}
