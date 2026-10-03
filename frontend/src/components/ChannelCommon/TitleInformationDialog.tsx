// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import type { ReactNode } from "react"
import type { TitleInformationOutput, TitleInformationSide } from "@/client"
import { TitlesService } from "@/client"
import { CollapsibleSection } from "@/components/ChannelCommon/CollapsibleSection"
import { InformationHeroLinks } from "@/components/ChannelCommon/InformationHero"
import {
  ExternalAnchor,
  type InformationRows,
  InformationTable,
} from "@/components/ChannelCommon/InformationTable"
import { ReportIssueForm } from "@/components/ChannelCommon/ReportIssueForm"
import { TitleSeasonsSection } from "@/components/ChannelCommon/TitleSeasonsSection"
import {
  FilledDescription,
  TitleSummaryLayout,
} from "@/components/Channels/TitleSummary"
import { Favicon } from "@/components/Common/Favicon"
import { ChannelsWithTitleLink } from "@/components/Titles/ChannelsWithTitleLink"
import { TitleTmdbSection } from "@/components/Titles/TitleTmdbSection"

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
function cardTitle(data: TitleInformationOutput) {
  return data.tmdb?.title ?? data.source.title
}

// TODO: Validate
function heroFacts(data: TitleInformationOutput) {
  if (data.source.source.plugin_name === "TMDB" || data.tmdb) {
    return []
  }
  return ["Not linked to TMDB"]
}

// TODO: Validate
function cataloguerOverlay(data: TitleInformationOutput) {
  const cataloguer = data.tmdb ?? data.source
  const faviconUrl = sideFavicon(cataloguer)
  if (!faviconUrl) {
    return null
  }
  return (
    <span className="absolute top-1 left-1 z-10 rounded bg-background/80 p-0.5">
      <Favicon src={faviconUrl} label={cataloguer.label} className="size-5" />
    </span>
  )
}

// TODO: Validate
function sideFavicon(side: TitleInformationSide) {
  if (side.source.favicon_url) {
    return side.source.favicon_url
  }
  return side.source.plugin_name === "TMDB" ? "/tmdb.svg" : null
}

// TODO: Validate
function sideLink(side: TitleInformationSide) {
  const href = side.title.tmdb_url ?? side.title.url
  if (!href) {
    return []
  }
  return [{ label: side.label, href, faviconUrl: sideFavicon(side) }]
}

// TODO: Validate
function heroLinks(data: TitleInformationOutput, extraLinks: HeroLink[]) {
  return [
    ...sideLink(data.source),
    ...(data.tmdb ? sideLink(data.tmdb) : []),
    ...(data.websites ?? []).flatMap(sideLink),
    ...extraLinks,
  ]
}

export interface HeroLink {
  label: string
  href: string
  faviconUrl?: string | null
}

interface TitleInformationPanelProps {
  titleId: string
  extraLinks?: HeroLink[]
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
function heroTitle(data: TitleInformationOutput) {
  const name = data.source.title.name ?? "Unnamed title"
  const year = data.source.title.year
  return year ? `${name} (${year})` : name
}

// TODO: Validate
function heroTitleWithSource(data: TitleInformationOutput) {
  const faviconUrl = sideFavicon(data.source)
  return (
    <>
      {faviconUrl && (
        <Favicon
          src={faviconUrl}
          label={data.source.label}
          className="mr-2 inline size-5 align-[-0.125em]"
        />
      )}
      {heroTitle(data)}
    </>
  )
}

// TODO: Validate
function showHero(
  data: TitleInformationOutput,
  facts: string[],
  links: HeroLink[],
) {
  const sourceTitle = data.source.title
  return (
    <div className="overflow-hidden rounded-md border bg-linear-to-br from-muted/60 to-background">
      <TitleSummaryLayout
        artwork={
          sourceTitle.poster_thumbnail_url ??
          sourceTitle.poster_url ??
          sourceTitle.thumbnail_url ??
          sourceTitle.image_url
        }
        artworkAlt={heroTitle(data)}
        artworkOverlay={cataloguerOverlay(data)}
        title={cardTitle(data)}
        stats={data.stats}
        details={data.details}
        heading={
          <h2 className="text-xl font-semibold wrap-break-word">
            {heroTitleWithSource(data)}
          </h2>
        }
        extraLines={facts}
        description={
          sourceTitle.description && (
            <FilledDescription text={sourceTitle.description} />
          )
        }
        footer={
          <InformationHeroLinks
            links={links}
            actions={<ChannelsWithTitleLink titleId={sourceTitle.id} />}
          />
        }
      />
    </div>
  )
}

// TODO: Validate
function summaryHero(data: TitleInformationOutput) {
  return showHero(data, [], sideLink(data.source))
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
/**
 * The title's own account of itself beside TMDB's, without a dialog around it,
 * so it can be read inside whatever is already open.
 */
export function TitleInformationPanel({
  titleId,
  enabled = true,
  extraLinks = [],
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
    <div className="flex flex-col gap-6">
      {showHero(data, heroFacts(data), heroLinks(data, extraLinks))}

      <TitleTmdbSection title={data.source.title} enabled={enabled} />

      <TitleSeasonsSection titleId={titleId} enabled={enabled} />

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

      <CollapsibleSection
        title="Report an issue"
        defaultOpen={data.issue_reports.length > 0}
      >
        <p className="mb-4 text-sm text-muted-foreground">
          Tell us what is wrong with this title on {data.source.label}.
        </p>
        <ReportIssueForm sources={[{ titleId, label: data.source.label }]} />
      </CollapsibleSection>
    </div>
  )
}
