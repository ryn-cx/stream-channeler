// TODO: Validate
import { ChevronDown, ChevronRight } from "lucide-react"
import { useState } from "react"

import type { WhitelistSourceOutput } from "@/client"
import { TitleInformationPanel } from "@/components/ChannelCommon/TitleInformationDialog"
import EditTitle from "@/components/Titles/Edit"
import { Button } from "@/components/ui/button"
import {
  AdminOnly,
  ExternalMediaLink,
  MediaPageButton,
} from "./MediaPageButton"

/** Every row one site carries the title under. */
export interface SourceGroup {
  sourceId: string
  sourceName: string | null
  faviconUrl: string | null
  isTmdb: boolean
  rows: WhitelistSourceOutput[]
}

// TODO: Validate
/** Gather the rows under the site carrying them, in the order they arrived. */
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
        label="Open this title on its site"
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
  informationTitleId: string | null
  onToggleInformation: (titleId: string) => void
  onToggleEnabled: (titleId: string) => void
}

// TODO: Validate
/**
 * One site, and the rows it carries the title under.
 *
 * A site carrying the title once is read as the row itself: opening it opens
 * that row's information, and the row's own controls sit on the site's line,
 * since a level holding one thing is a level nobody wants to open. A site
 * carrying it more than once opens instead into the rows it holds, each of
 * which opens its own information.
 */
// TODO: Validate
export function SourceGroupRow({
  group,
  isWhitelist,
  enabledSourceIds,
  informationTitleId,
  onToggleInformation,
  onToggleEnabled,
}: SourceGroupRowProps) {
  const [expanded, setExpanded] = useState(false)
  const single = group.rows.length === 1 ? group.rows[0] : null

  // TODO: Validate
  const actionLabel = (titleId: string) => {
    const enabled = enabledSourceIds.has(titleId)
    if (isWhitelist)
      return enabled ? "Remove from Whitelist" : "Add to Whitelist"
    return enabled ? "Remove from Blacklist" : "Add to Blacklist"
  }

  // TODO: Validate
  const markButton = (row: WhitelistSourceOutput) =>
    group.isTmdb ? (
      <span className="text-xs text-muted-foreground">Catalogue only</span>
    ) : (
      <Button
        variant={enabledSourceIds.has(row.title_id) ? "default" : "outline"}
        size="sm"
        onClick={() => onToggleEnabled(row.title_id)}
      >
        {actionLabel(row.title_id)}
      </Button>
    )

  const isOpen = single ? informationTitleId === single.title_id : expanded
  // TODO: Validate
  const toggleOpen = () =>
    single ? onToggleInformation(single.title_id) : setExpanded(!expanded)

  return (
    <div>
      <div className="flex items-center gap-2 p-2 hover:bg-accent/30 rounded">
        <Button variant="ghost" size="icon-sm" onClick={toggleOpen}>
          {isOpen ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </Button>
        {group.faviconUrl && (
          <img
            referrerPolicy="no-referrer"
            src={group.faviconUrl}
            alt=""
            className="size-6 shrink-0"
          />
        )}
        <button
          type="button"
          className="flex-1 text-left text-sm hover:underline"
          onClick={toggleOpen}
        >
          {group.sourceName ?? "Unknown source"}
          {single ? null : (
            <span className="ml-2 text-xs text-muted-foreground">
              {group.rows.length} titles
            </span>
          )}
        </button>
        {single ? markButton(single) : null}
        {single ? <RowControls row={single} /> : null}
        <MediaPageButton
          to="/titles"
          search={{ source_id: group.sourceId }}
          label="Open this source here"
        />
      </div>

      {single && isOpen && (
        <div className="rounded border bg-muted/30 p-4">
          <TitleInformationPanel titleId={single.title_id} />
        </div>
      )}

      {!single && expanded && (
        <div className="ml-8 space-y-1 border-l pl-2">
          {group.rows.map((row) => (
            <div key={row.title_id}>
              <div className="flex items-center gap-2 p-2 hover:bg-accent/30 rounded">
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={() => onToggleInformation(row.title_id)}
                >
                  {informationTitleId === row.title_id ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                </Button>
                <button
                  type="button"
                  className="flex-1 text-left text-sm hover:underline"
                  onClick={() => onToggleInformation(row.title_id)}
                >
                  {row.title.name ?? row.title.key}
                </button>
                {markButton(row)}
                <RowControls row={row} />
              </div>
              {informationTitleId === row.title_id && (
                <div className="rounded border bg-muted/30 p-4">
                  <TitleInformationPanel titleId={row.title_id} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
