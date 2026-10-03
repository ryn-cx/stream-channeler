// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import type { SeasonInformationSide } from "@/client"
import { SeasonsService } from "@/client"
import { CollapsibleSection } from "@/components/ChannelCommon/CollapsibleSection"
import {
  ExternalAnchor,
  type InformationRows,
  InformationTable,
} from "@/components/ChannelCommon/InformationTable"
import { IssueReportsSection } from "@/components/ChannelCommon/IssueReportsSection"

// TODO: Validate
function sideRows(side: SeasonInformationSide): InformationRows {
  const season = side.season
  return {
    Name: season.name,
    "Season number": season.season_number,
    "Sort order": season.sort_order,
    Title: side.title.name,
    Link: season.url ? (
      <ExternalAnchor href={season.url} label={season.url} />
    ) : null,
    Image: season.image_url ? (
      <ExternalAnchor href={season.image_url} label={season.image_url} />
    ) : null,
    Key: season.key,
  }
}

const ROW_LABELS = [
  "Name",
  "Season number",
  "Sort order",
  "Title",
  "Link",
  "Image",
  "Key",
]

// TODO: Validate
function SeasonInformation({
  seasonId,
  enabled,
}: {
  seasonId: string
  enabled: boolean
}) {
  const queryKey = ["season-information", seasonId]
  const { data, isLoading, error } = useQuery({
    queryKey,
    queryFn: () => SeasonsService.getSeasonInformation({ seasonId }),
    enabled,
    staleTime: 5 * 60 * 1000,
  })

  if (isLoading) {
    return (
      <p className="text-sm text-muted-foreground">
        Loading season information…
      </p>
    )
  }
  if (error || !data) {
    return (
      <p className="text-sm text-muted-foreground">
        Couldn't load the season information.
      </p>
    )
  }

  return (
    <div className="flex flex-col">
      <CollapsibleSection title="Full Information">
        <div className="overflow-x-auto">
          <InformationTable
            sourceLabel={data.source.label}
            tmdbLabel={data.tmdb ? data.tmdb.label : "TMDB (not linked)"}
            rowLabels={ROW_LABELS}
            sourceRows={sideRows(data.source)}
            tmdbRows={data.tmdb ? sideRows(data.tmdb) : null}
          />
        </div>
      </CollapsibleSection>

      <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        <dt className="text-muted-foreground">Season identifier</dt>
        <dd className="break-all">{data.source.season.id}</dd>
      </dl>

      <IssueReportsSection
        target="season"
        mediaId={seasonId}
        reports={data.issue_reports}
        informationQueryKey={queryKey}
      />
    </div>
  )
}

interface SeasonInformationPanelProps {
  seasonIds: string[]
  /** Whether the information is wanted yet, so a collapsed panel fetches nothing. */
  enabled?: boolean
}

// TODO: Validate
/**
 * Each stored season the row stands for, without a dialog around it, so they can
 * be read inside whatever is already open.
 */
export function SeasonInformationPanel({
  seasonIds,
  enabled = true,
}: SeasonInformationPanelProps) {
  return (
    <div className="flex flex-col gap-8">
      {seasonIds.map((seasonId) => (
        <SeasonInformation
          key={seasonId}
          seasonId={seasonId}
          enabled={enabled}
        />
      ))}
    </div>
  )
}
