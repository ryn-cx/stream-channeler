// TODO: Validate
import type { WhitelistSourceOutput } from "@/client"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"

// TODO: Validate
/** The favicons of the websites' links a season or episode was found on. */
// TODO: Validate
export function SourceFavicons({
  showIds,
  sourcesByShowId,
}: {
  showIds: string[]
  sourcesByShowId: Map<string, WhitelistSourceOutput>
}) {
  return (
    <span className="flex items-center gap-1 shrink-0">
      {showIds.map((showId) => {
        const source = sourcesByShowId.get(showId)
        if (!source?.favicon_url) return null
        return (
          <Tooltip key={showId}>
            <TooltipTrigger asChild>
              <img
                referrerPolicy="no-referrer"
                src={source.favicon_url}
                alt={`${source.source_name} favicon`}
                className="size-6 shrink-0"
              />
            </TooltipTrigger>
            <TooltipContent>
              {source.source_name ?? "Unknown source"}
            </TooltipContent>
          </Tooltip>
        )
      })}
    </span>
  )
}
