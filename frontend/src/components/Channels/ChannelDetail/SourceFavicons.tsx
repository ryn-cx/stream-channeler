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
  titleIds,
  sourcesByTitleId,
}: {
  titleIds: string[]
  sourcesByTitleId: Map<string, WhitelistSourceOutput>
}) {
  return (
    <span className="flex items-center gap-1 shrink-0">
      {titleIds.map((titleId) => {
        const source = sourcesByTitleId.get(titleId)
        if (!source?.favicon_url) return null
        return (
          <Tooltip key={titleId}>
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
