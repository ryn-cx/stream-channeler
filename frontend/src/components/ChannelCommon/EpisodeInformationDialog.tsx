// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import type { EpisodeInformationSide } from "@/client"
import { EpisodesService } from "@/client"
import { EpisodeTmdbLinkMenu } from "@/components/Admin/EpisodeTmdbLinkMenu"
import { CollapsibleSection } from "@/components/ChannelCommon/CollapsibleSection"
import {
  EpisodeInformationHero,
  episodeInformationQueryKey,
  formatDuration,
} from "@/components/ChannelCommon/EpisodeInformationHero"
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

// TODO: Validate
function sideRows(side: EpisodeInformationSide): InformationRows {
  return {
    Name: side.name,
    "Episode number": side.episode_number,
    "Sort order": side.sort_order,
    "Season number": side.season_number,
    "Season name": side.season_name,
    Show: side.show_name,
    Duration: formatDuration(side.duration),
    "Air date": formatInformationDate(side.air_date),
    Description: side.description,
    Link: side.url ? <ExternalAnchor href={side.url} label={side.url} /> : null,
    Image: side.image_url ? (
      <ExternalAnchor href={side.image_url} label={side.image_url} />
    ) : null,
    Key: side.key,
    "Link locked": side.canonical_episode_locked ? "Yes" : "No",
    "Link note": side.canonical_episode_note,
    "Data timestamp": formatInformationDate(side.data_timestamp),
    "Update at": formatInformationDate(side.update_at),
    "Modified at": formatInformationDate(side.modified_at),
  }
}

const ROW_LABELS = [
  "Name",
  "Episode number",
  "Sort order",
  "Season number",
  "Season name",
  "Show",
  "Duration",
  "Air date",
  "Description",
  "Link",
  "Image",
  "Key",
  "Episode identifier",
  "Identifier locked",
  "Identifier note",
  "Data timestamp",
  "Update at",
  "Modified at",
]

interface EpisodeInformationPanelProps {
  episodeId: string
  /** Whether the information is wanted yet, so a collapsed panel fetches nothing. */
  enabled?: boolean
  /**
   * Whether the website's own row is what was opened, in which case that is what
   * is shown rather than TMDB's account of the episode it was matched to.
   */
  preferSource?: boolean
}

// TODO: Validate
/**
 * The episode's own account of itself beside TMDB's, without a dialog around it,
 * so it can be read inside whatever is already open.
 */
export function EpisodeInformationPanel({
  episodeId,
  enabled = true,
  preferSource = false,
}: EpisodeInformationPanelProps) {
  const queryKey = episodeInformationQueryKey(episodeId)
  const { data, isLoading, error } = useQuery({
    queryKey,
    queryFn: () => EpisodesService.getEpisodeInformation({ episodeId }),
    enabled,
    staleTime: 5 * 60 * 1000,
  })

  if (isLoading) {
    return (
      <p className="text-sm text-muted-foreground">
        Loading episode information…
      </p>
    )
  }
  if (error || !data) {
    return (
      <p className="text-sm text-muted-foreground">
        Couldn't load the episode information.
      </p>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <EpisodeInformationHero
        episodeId={episodeId}
        enabled={enabled}
        preferSource={preferSource}
      />

      <CollapsibleSection title="Field comparison">
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

      <IssueReportsSection
        target="episode"
        mediaId={episodeId}
        reports={data.issue_reports}
        informationQueryKey={queryKey}
      />

      <EpisodeTmdbLinkMenu
        episodeId={episodeId}
        name={data.source.name}
        seasonNumber={data.source.season_number}
        episodeNumber={data.source.episode_number}
        informationQueryKey={queryKey}
      />
    </div>
  )
}

// TODO: Validate
export function EpisodeInformationDialog({
  episodeId,
  open,
  onOpenChange,
}: EpisodeInformationDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <ModalContent size="full">
        <DialogHeader>
          <DialogTitle>Episode Information</DialogTitle>
          <DialogDescription>
            What the source and TMDB each say about this episode. The episode is
            shown as TMDB has it wherever TMDB has anything to say.
          </DialogDescription>
        </DialogHeader>

        <DialogBody className="overflow-x-auto">
          <EpisodeInformationPanel episodeId={episodeId} enabled={open} />
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
