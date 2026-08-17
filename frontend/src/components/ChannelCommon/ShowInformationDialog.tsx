// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import type { ShowInformationOutput, ShowInformationSide } from "@/client"
import { ShowsService } from "@/client"
import { AddToChannelButton } from "@/components/ChannelCommon/AddToChannelButton"
import { CollapsibleSection } from "@/components/ChannelCommon/CollapsibleSection"
import { InformationHero } from "@/components/ChannelCommon/InformationHero"
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

interface ShowInformationDialogProps {
  showId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

// TODO: Validate
function sideRows(side: ShowInformationSide): InformationRows {
  return {
    Name: side.name,
    "Media type": side.media_type,
    Description: side.description,
    Link: side.url ? <ExternalAnchor href={side.url} label={side.url} /> : null,
    Image: side.image_url ? (
      <ExternalAnchor href={side.image_url} label={side.image_url} />
    ) : null,
    Key: side.key,
  }
}

const ROW_LABELS = ["Name", "Media type", "Description", "Link", "Image", "Key"]

// TODO: Validate
function heroFacts(data: ShowInformationOutput) {
  const facts = [data.source.media_type]
  facts.push(data.tmdb ? "Linked to TMDB" : "Not linked to TMDB")
  facts.push(data.source.label)
  return facts.filter((fact): fact is string => !!fact)
}

// TODO: Validate
function heroLinks(data: ShowInformationOutput) {
  const links = []
  if (data.source.url) {
    links.push({ label: data.source.label, href: data.source.url })
  }
  if (data.tmdb?.url) {
    links.push({ label: data.tmdb.label, href: data.tmdb.url })
  }
  return links
}

interface ShowInformationPanelProps {
  showId: string
  /** Whether the information is wanted yet, so a collapsed panel fetches nothing. */
  enabled?: boolean
}

// TODO: Validate
function useShowInformation(showId: string, enabled: boolean) {
  const queryKey = ["show-information", showId]
  const query = useQuery({
    queryKey,
    queryFn: () => ShowsService.getShowInformation({ showId }),
    enabled,
    staleTime: 5 * 60 * 1000,
  })
  return { queryKey, ...query }
}

// TODO: Validate
function showHero(
  data: ShowInformationOutput,
  facts: string[],
  links: { label: string; href: string }[],
) {
  return (
    <InformationHero
      title={data.source.name ?? "Unnamed show"}
      description={data.source.description}
      imageUrl={data.source.image_url}
      facts={facts}
      links={links}
    />
  )
}

// TODO: Validate
/**
 * What the title is, without whether it reached TMDB.
 *
 * Read where the title itself is what is open rather than the match between two
 * accounts of it, and where the row being read may be TMDB's own: a canonical
 * row is linked to nothing, which the linked/not-linked fact would report as
 * having failed to reach the very record it is.
 */
function summaryFacts(data: ShowInformationOutput) {
  const facts = [data.source.media_type, data.source.label]
  return facts.filter((fact): fact is string => !!fact)
}

// TODO: Validate
function summaryHero(data: ShowInformationOutput) {
  const links = data.source.url
    ? [{ label: data.source.label, href: data.source.url }]
    : []
  return showHero(data, summaryFacts(data), links)
}

// TODO: Validate
/**
 * The title as it reads at a glance with the issues reported against it, for
 * whatever is already open on that title and has no room for the comparison.
 */
export function ShowInformationSummary({
  showId,
  enabled = true,
}: ShowInformationPanelProps) {
  const { data, isLoading, error } = useShowInformation(showId, enabled)

  if (isLoading) {
    return (
      <p className="text-sm text-muted-foreground">Loading show information…</p>
    )
  }
  if (error || !data) {
    return (
      <p className="text-sm text-muted-foreground">
        Couldn't load the show information.
      </p>
    )
  }

  return (
    <div className="flex flex-col gap-2">
      {summaryHero(data)}
      <AddToChannelButton showId={data.show_id} showUrl={data.source.url} />
    </div>
  )
}

// TODO: Validate
export function ShowIssueReports({
  showId,
  enabled = true,
}: ShowInformationPanelProps) {
  const { queryKey, data, isLoading, error } = useShowInformation(
    showId,
    enabled,
  )

  if (isLoading || error || !data) {
    return null
  }

  return (
    <IssueReportsSection
      target="show"
      mediaId={showId}
      reports={data.issue_reports}
      informationQueryKey={queryKey}
    />
  )
}

// TODO: Validate
/**
 * The title's own account of itself beside TMDB's, without a dialog around it,
 * so it can be read inside whatever is already open.
 */
export function ShowInformationPanel({
  showId,
  enabled = true,
}: ShowInformationPanelProps) {
  const { queryKey, data, isLoading, error } = useShowInformation(
    showId,
    enabled,
  )

  if (isLoading) {
    return (
      <p className="text-sm text-muted-foreground">Loading show information…</p>
    )
  }
  if (error || !data) {
    return (
      <p className="text-sm text-muted-foreground">
        Couldn't load the show information.
      </p>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      {showHero(data, heroFacts(data), heroLinks(data))}

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

      <div className="grid items-start gap-4 sm:grid-cols-2">
        <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
          <dt className="text-muted-foreground">Link locked</dt>
          <dd>{data.canonical_show_locked ? "Yes" : "No"}</dd>
        </dl>

        <IssueReportsSection
          target="show"
          mediaId={showId}
          reports={data.issue_reports}
          informationQueryKey={queryKey}
        />
      </div>
    </div>
  )
}

// TODO: Validate
export function ShowInformationDialog({
  showId,
  open,
  onOpenChange,
}: ShowInformationDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <ModalContent size="full">
        <DialogHeader>
          <DialogTitle>Show Information</DialogTitle>
          <DialogDescription>
            What the source and TMDB each say about this title. The title is
            shown as this source has it, with TMDB's account beside it in the
            comparison below.
          </DialogDescription>
        </DialogHeader>

        <DialogBody className="overflow-x-auto">
          <ShowInformationPanel showId={showId} enabled={open} />
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
