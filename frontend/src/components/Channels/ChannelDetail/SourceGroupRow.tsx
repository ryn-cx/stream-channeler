// TODO: Validate

import type { WhitelistSourceOutput } from "@/client"
import { Favicon } from "@/components/Common/Favicon"
import EditTitle from "@/components/Titles/Edit"
import { Button } from "@/components/ui/button"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { useOpenMedia } from "@/hooks/useOpenMedia"
import { AdminOnly, ExternalMediaLink } from "./MediaPageButton"

/** Every row one site lists the title under. */
export interface SourceGroup {
  sourceId: string
  sourceName: string | null
  faviconUrl: string | null
  isTmdb: boolean
  rows: WhitelistSourceOutput[]
}

// TODO: Validate
/** Gather the rows under the site listing them, in the order they arrived. */
export function groupBySource(sources: WhitelistSourceOutput[]): SourceGroup[] {
  const groups = new Map<string, SourceGroup>()
  for (const source of sources) {
    const group = groups.get(source.source_id) ?? {
      sourceId: source.source_id,
      sourceName: source.source_key,
      faviconUrl: source.favicon_url,
      isTmdb: source.is_tmdb ?? false,
      rows: [],
    }
    group.rows.push(source)
    groups.set(source.source_id, group)
  }
  return [...groups.values()]
}

// TODO: Validate
/** The controls that belong to one row, whatever level it is read at. */
function RowControls({ row }: { row: WhitelistSourceOutput }) {
  return (
    <>
      <ExternalMediaLink
        url={row.title.url}
        label={`Open ${row.title.name ?? row.title.key} on ${
          row.source_key ?? "its site"
        }`}
      />
      <AdminOnly>
        <EditTitle title={row.title} />
      </AdminOnly>
    </>
  )
}

interface SourceGroupRowProps {
  group: SourceGroup
  isWhitelist: boolean
  enabledSourceIds: Set<string>
  onToggleEnabled: (titleId: string) => void
}

// TODO: Validate
/**
 * One site's rows of the table, one per title it lists the title under.
 *
 * The site names itself once, on a cell down the rows it holds, so the titles
 * and the controls that mark them line up across every site.
 */
// TODO: Validate
export function SourceGroupRow({
  group,
  isWhitelist,
  enabledSourceIds,
  onToggleEnabled,
}: SourceGroupRowProps) {
  const openMedia = useOpenMedia()
  // TODO: Validate
  const actionLabel = (titleId: string) => {
    const enabled = enabledSourceIds.has(titleId)
    if (isWhitelist) return enabled ? "Unwhitelist" : "Whitelist"
    return enabled ? "Unblacklist" : "Blacklist"
  }

  // TODO: Validate
  const actionDescription = (row: WhitelistSourceOutput) => {
    const enabled = enabledSourceIds.has(row.title_id)
    const titleName = row.title.name ?? row.title.key
    const siteName = row.source_key ?? "this site"
    if (isWhitelist) {
      return enabled
        ? `Stop watching ${siteName} for ${titleName}.`
        : `Watch ${siteName} for ${titleName}, and only the sites whitelisted here.`
    }
    return enabled
      ? `Watch ${siteName} for ${titleName} again.`
      : `Stop watching ${siteName} for ${titleName}.`
  }

  // TODO: Validate
  const markButton = (row: WhitelistSourceOutput) =>
    group.isTmdb ? (
      <span className="text-xs text-muted-foreground">Catalogue only</span>
    ) : (
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant={enabledSourceIds.has(row.title_id) ? "default" : "outline"}
            size="sm"
            onClick={() => onToggleEnabled(row.title_id)}
          >
            {actionLabel(row.title_id)}
          </Button>
        </TooltipTrigger>
        <TooltipContent>{actionDescription(row)}</TooltipContent>
      </Tooltip>
    )

  return (
    <tbody className="border-b last:border-b-0">
      {group.rows.map((row, index) => (
        <tr
          key={row.title_id}
          className="cursor-pointer hover:bg-accent/30"
          onClick={() => openMedia({ kind: "title", titleId: row.title_id })}
        >
          <td className="whitespace-nowrap p-2 pr-4 align-top">
            {index === 0 && (
              <div className="flex items-center gap-2">
                {group.faviconUrl && (
                  <Favicon
                    src={group.faviconUrl}
                    label={group.sourceName ?? "Unknown source"}
                    className="size-6"
                    tooltip={false}
                  />
                )}
                <span className="text-sm">
                  {group.sourceName ?? "Unknown source"}
                </span>
              </div>
            )}
          </td>
          <td className="w-full p-2">
            <span className="flex items-center gap-1 text-sm">
              <span>{row.title.name ?? row.title.key}</span>
            </span>
          </td>
          <td
            className="whitespace-nowrap p-2 align-top"
            onClick={(event) => event.stopPropagation()}
            onKeyDown={(event) => event.stopPropagation()}
          >
            <div className="flex items-center justify-end gap-1">
              {markButton(row)}
              <RowControls row={row} />
            </div>
          </td>
        </tr>
      ))}
    </tbody>
  )
}
