// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import type { EpisodeInformationOutput, EpisodeInformationSide } from "@/client"
import { EpisodesService } from "@/client"
import { CollapsibleSection } from "@/components/ChannelCommon/CollapsibleSection"
import { InformationHero } from "@/components/ChannelCommon/InformationHero"
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
function formatDuration(value: number | null) {
  if (value == null) return null
  const minutes = Math.floor(value / 60)
  const seconds = value % 60
  return `${value}s (${minutes}m ${seconds}s)`
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

// TODO: Validate
function heroSubtitle(data: EpisodeInformationOutput) {
  const side = data.tmdb ?? data.source
  const seasonNumber = side.season_number ?? data.source.season_number
  const episodeNumber = side.episode_number ?? data.source.episode_number
  const placement = [
    seasonNumber != null ? `Season ${seasonNumber}` : side.season_name,
    episodeNumber != null ? `Episode ${episodeNumber}` : null,
  ].filter(Boolean)
  return [side.show_name, ...placement].filter(Boolean).join(" · ")
}

// TODO: Validate
function heroFacts(data: EpisodeInformationOutput) {
  const side = data.tmdb ?? data.source
  const facts = [
    formatDuration(side.duration ?? data.source.duration),
    formatInformationDate(side.air_date ?? data.source.air_date),
    data.tmdb ? "Linked to TMDB" : "Not linked to TMDB",
    data.source.label,
  ]
  return facts.filter((fact): fact is string => !!fact)
}

// TODO: Validate
function heroLinks(data: EpisodeInformationOutput) {
  const links = []
  if (data.source.url) {
    links.push({ label: data.source.label, href: data.source.url })
  }
  if (data.tmdb?.url) {
    links.push({ label: data.tmdb.label, href: data.tmdb.url })
  }
  return links
}

interface EpisodeInformationPanelProps {
  episodeId: string
  /** Whether the information is wanted yet, so a collapsed panel fetches nothing. */
  enabled?: boolean
}

// TODO: Validate
/**
 * The episode's own account of itself beside TMDB's, without a dialog around it,
 * so it can be read inside whatever is already open.
 */
export function EpisodeInformationPanel({
  episodeId,
  enabled = true,
}: EpisodeInformationPanelProps) {
  const queryKey = ["episode-information", episodeId]
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
      <InformationHero
        title={data.tmdb?.name ?? data.source.name ?? "Unnamed episode"}
        subtitle={heroSubtitle(data)}
        description={data.tmdb?.description ?? data.source.description}
        imageUrl={data.tmdb?.image_url ?? data.source.image_url}
        facts={heroFacts(data)}
        links={heroLinks(data)}
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
