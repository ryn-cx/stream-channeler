// TODO: Validate
import type { WhitelistSourceOutput } from "@/client"
import { Favicon } from "@/components/Common/Favicon"

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
          <Favicon
            key={titleId}
            src={source.favicon_url}
            label={source.source_key}
            className="size-6"
          />
        )
      })}
    </span>
  )
}
