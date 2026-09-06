// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import type { ReactNode } from "react"
import type { TitleInformationOutput, TitleInformationSide } from "@/client"
import { TitlesService } from "@/client"
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

interface TitleInformationDialogProps {
  titleId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

// TODO: Validate
function sideRows(side: TitleInformationSide): InformationRows {
  const title = side.title
  return {
    Name: title.name,
    "Media type": title.media_type,
    Description: title.description,
    Link: title.url ? (
      <ExternalAnchor href={title.url} label={title.url} />
    ) : null,
    Image: title.image_url ? (
      <ExternalAnchor href={title.image_url} label={title.image_url} />
    ) : null,
    Key: title.key,
  }
}

const ROW_LABELS = ["Name", "Media type", "Description", "Link", "Image", "Key"]

// TODO: Validate
function heroFacts(data: TitleInformationOutput) {
  const facts = [data.source.title.media_type]
  facts.push(data.tmdb ? "Linked to TMDB" : "Not linked to TMDB")
  facts.push(data.source.label)
  return facts.filter((fact): fact is string => !!fact)
}

// TODO: Validate
function heroLinks(data: TitleInformationOutput) {
  const links = []
  if (data.source.title.url) {
    links.push({ label: data.source.label, href: data.source.title.url })
  }
  if (data.tmdb?.title.url) {
    links.push({ label: data.tmdb.label, href: data.tmdb.title.url })
  }
  return links
}

interface TitleInformationPanelProps {
  titleId: string
  /** Whether the information is wanted yet, so a collapsed panel fetches nothing. */
  enabled?: boolean
  children?: ReactNode
}

// TODO: Validate
function useTitleInformation(titleId: string, enabled: boolean) {
  const queryKey = ["title-information", titleId]
  const query = useQuery({
    queryKey,
    queryFn: () => TitlesService.getTitleInformation({ titleId }),
    enabled,
    staleTime: 5 * 60 * 1000,
  })
  return { queryKey, ...query }
}

// TODO: Validate
function showHero(
  data: TitleInformationOutput,
  facts: string[],
  links: { label: string; href: string }[],
) {
  return (
    <InformationHero
      title={data.source.title.name ?? "Unnamed title"}
      description={data.source.title.description}
      imageUrl={data.source.title.thumbnail_url ?? data.source.title.image_url}
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
function summaryFacts(data: TitleInformationOutput) {
  const facts = [data.source.title.media_type, data.source.label]
  return facts.filter((fact): fact is string => !!fact)
}

// TODO: Validate
function summaryHero(data: TitleInformationOutput) {
  const links = data.source.title.url
    ? [{ label: data.source.label, href: data.source.title.url }]
    : []
  return showHero(data, summaryFacts(data), links)
}

// TODO: Validate
/**
 * The title as it reads at a glance with the issues reported against it, for
 * whatever is already open on that title and has no room for the comparison.
 */
export function TitleInformationSummary({
  titleId,
  enabled = true,
  children,
}: TitleInformationPanelProps) {
  const { data, isLoading, error } = useTitleInformation(titleId, enabled)

  if (isLoading) {
    return (
      <p className="text-sm text-muted-foreground">
        Loading title information…
      </p>
    )
  }
  if (error || !data) {
    return (
      <p className="text-sm text-muted-foreground">
        Couldn't load the title information.
      </p>
    )
  }

  return (
    <div className="flex flex-col gap-2">
      {summaryHero(data)}
      {children}
    </div>
  )
}

// TODO: Validate
export function TitleIssueReports({
  titleId,
  enabled = true,
}: TitleInformationPanelProps) {
  const { queryKey, data, isLoading, error } = useTitleInformation(
    titleId,
    enabled,
  )

  if (isLoading || error || !data) {
    return null
  }

  return (
    <IssueReportsSection
      target="title"
      mediaId={titleId}
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
export function TitleInformationPanel({
  titleId,
  enabled = true,
}: TitleInformationPanelProps) {
  const { queryKey, data, isLoading, error } = useTitleInformation(
    titleId,
    enabled,
  )

  if (isLoading) {
    return (
      <p className="text-sm text-muted-foreground">
        Loading title information…
      </p>
    )
  }
  if (error || !data) {
    return (
      <p className="text-sm text-muted-foreground">
        Couldn't load the title information.
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
          <dt className="text-muted-foreground">Link validated at</dt>
          <dd>
            {formatInformationDate(
              data.source.title.canonical_title_validated_at,
            )}
          </dd>
        </dl>

        <IssueReportsSection
          target="title"
          mediaId={titleId}
          reports={data.issue_reports}
          informationQueryKey={queryKey}
        />
      </div>
    </div>
  )
}

// TODO: Validate
export function TitleInformationDialog({
  titleId,
  open,
  onOpenChange,
}: TitleInformationDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <ModalContent size="full">
        <DialogHeader>
          <DialogTitle>Title Information</DialogTitle>
          <DialogDescription>
            What the source and TMDB each say about this title. The title is
            shown as this source has it, with TMDB's account beside it in the
            comparison below.
          </DialogDescription>
        </DialogHeader>

        <DialogBody className="overflow-x-auto">
          <TitleInformationPanel titleId={titleId} enabled={open} />
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
