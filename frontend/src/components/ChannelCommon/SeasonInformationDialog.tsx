// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import type { SeasonInformationSide } from "@/client"
import { SeasonsService } from "@/client"
import {
  ExternalAnchor,
  type InformationRows,
  InformationTable,
} from "@/components/ChannelCommon/InformationTable"
import { IssueReportsSection } from "@/components/ChannelCommon/IssueReportsSection"
import { ModalContent } from "@/components/Common/ModalContent"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogBody,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

interface SeasonInformationDialogProps {
  /**
   * The stored seasons the row stands for. A website can split one TMDB season
   * into several of its own, so a row can cover more than one, and each is laid
   * out on its own.
   */
  seasonIds: string[]
  open: boolean
  onOpenChange: (open: boolean) => void
}

function sideRows(side: SeasonInformationSide): InformationRows {
  return {
    Name: side.name,
    "Season number": side.season_number,
    "Sort order": side.sort_order,
    Show: side.show_name,
    Link: side.url ? <ExternalAnchor href={side.url} label={side.url} /> : null,
    Image: side.image_url ? (
      <ExternalAnchor href={side.image_url} label={side.image_url} />
    ) : null,
    Key: side.key,
  }
}

const ROW_LABELS = [
  "Name",
  "Season number",
  "Sort order",
  "Show",
  "Link",
  "Image",
  "Key",
]

function SeasonInformation({
  seasonId,
  open,
}: {
  seasonId: string
  open: boolean
}) {
  const queryKey = ["season-information", seasonId]
  const { data, isLoading, error } = useQuery({
    queryKey,
    queryFn: () => SeasonsService.getSeasonInformation({ seasonId }),
    enabled: open,
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
      <InformationTable
        sourceLabel={data.source.label}
        tmdbLabel={data.tmdb ? data.tmdb.label : "TMDB (not linked)"}
        rowLabels={ROW_LABELS}
        sourceRows={sideRows(data.source)}
        tmdbRows={data.tmdb ? sideRows(data.tmdb) : null}
      />

      <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        <dt className="text-muted-foreground">Season identifier</dt>
        <dd className="break-all">{data.season_identifier}</dd>
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

export function SeasonInformationDialog({
  seasonIds,
  open,
  onOpenChange,
}: SeasonInformationDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <ModalContent size="4xl">
        <DialogHeader>
          <DialogTitle>Season Information</DialogTitle>
          <DialogDescription>
            What the source and TMDB each say about this season. The season is
            shown as TMDB has it wherever TMDB has anything to say.
          </DialogDescription>
        </DialogHeader>

        <DialogBody className="flex flex-col gap-8 overflow-x-auto">
          {seasonIds.map((seasonId) => (
            <SeasonInformation key={seasonId} seasonId={seasonId} open={open} />
          ))}
        </DialogBody>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </ModalContent>
    </Dialog>
  )
}
