// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import type { EpisodeInformationSide } from "@/client"
import { EpisodesService } from "@/client"
import {
  ExternalAnchor,
  formatInformationDate,
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

interface EpisodeInformationDialogProps {
  episodeId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

function formatDuration(value: number | null) {
  if (value == null) return null
  const minutes = Math.floor(value / 60)
  const seconds = value % 60
  return `${value}s (${minutes}m ${seconds}s)`
}

function sideRows(side: EpisodeInformationSide): InformationRows {
  return {
    Name: side.name,
    "Episode number": side.episode_number,
    "Season number": side.season_number,
    "Season name": side.season_name,
    Show: side.show_name,
    Duration: formatDuration(side.duration),
    "Release date": formatInformationDate(side.release_date),
    "Air date": formatInformationDate(side.air_date),
    Description: side.description,
    Link: side.url ? <ExternalAnchor href={side.url} label={side.url} /> : null,
    Image: side.image_url ? (
      <ExternalAnchor href={side.image_url} label={side.image_url} />
    ) : null,
    Key: side.key,
  }
}

const ROW_LABELS = [
  "Name",
  "Episode number",
  "Season number",
  "Season name",
  "Show",
  "Duration",
  "Release date",
  "Air date",
  "Description",
  "Link",
  "Image",
  "Key",
]

export function EpisodeInformationDialog({
  episodeId,
  open,
  onOpenChange,
}: EpisodeInformationDialogProps) {
  const queryKey = ["episode-information", episodeId]
  const { data, isLoading, error } = useQuery({
    queryKey,
    queryFn: () => EpisodesService.getEpisodeInformation({ episodeId }),
    enabled: open,
    staleTime: 5 * 60 * 1000,
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <ModalContent size="4xl">
        <DialogHeader>
          <DialogTitle>Episode Information</DialogTitle>
          <DialogDescription>
            What the source and TMDB each say about this episode. The episode is
            shown as TMDB has it wherever TMDB has anything to say.
          </DialogDescription>
        </DialogHeader>

        <DialogBody className="overflow-x-auto">
          {isLoading ? (
            <p className="text-sm text-muted-foreground">
              Loading episode information…
            </p>
          ) : error || !data ? (
            <p className="text-sm text-muted-foreground">
              Couldn't load the episode information.
            </p>
          ) : (
            <>
              <InformationTable
                sourceLabel={data.source.label}
                tmdbLabel={data.tmdb ? data.tmdb.label : "TMDB (not linked)"}
                rowLabels={ROW_LABELS}
                sourceRows={sideRows(data.source)}
                tmdbRows={data.tmdb ? sideRows(data.tmdb) : null}
              />

              <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
                <dt className="text-muted-foreground">Episode identifier</dt>
                <dd className="break-all">{data.episode_identifier}</dd>
                <dt className="text-muted-foreground">Identifier locked</dt>
                <dd>{data.episode_identifier_locked ? "Yes" : "No"}</dd>
              </dl>

              <IssueReportsSection
                target="episode"
                mediaId={episodeId}
                reports={data.issue_reports}
                informationQueryKey={queryKey}
              />
            </>
          )}
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
