// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { Fragment, type ReactNode } from "react"
import type { ChannelTitleStats, TitleCardDetails } from "@/client"
import { UsersService } from "@/client"
import {
  FilledDescription,
  TitleSummaryLayout,
} from "@/components/Channels/TitleSummary"
import { Favicon } from "@/components/Common/Favicon"
import { Card } from "@/components/ui/card"
import { isLoggedIn } from "@/hooks/useAuth"

export interface Title {
  id: string
  name?: string | null
  source_id: string
  url?: string | null
  media_type?: string | null
  tmdb_id?: number | null
  tmdb_title_id?: string | null
  image_url?: string | null
  thumbnail_url?: string | null
  poster_url?: string | null
  poster_thumbnail_url?: string | null
  description?: string | null
  original_language?: string | null
  year?: number | null
  tmdb_score?: number | null
  tmdb_popularity?: number | null
  imdb_score?: number | null
  imdb_popularity?: number | null
}

export interface Source {
  key: string
  favicon_url?: string | null
  name?: string | null
}

// One card: the title, and every website's row standing for it. The title is
// what a card's actions are about, so it is named by `tmdbTitleId` rather
// than by any of the rows, which a website that files two titles under one page
// leaves standing for both.
export interface TitleGroup {
  tmdbTitleId: string
  name: string
}

const OTHER_SOURCE_KEY = "Other"

// TODO: Validate
/** The source's favicon, naming the source when it is hovered. */
// TODO: Validate
function SourceFavicon({
  source,
  disabled,
  className = "size-8",
}: {
  source: Source | undefined
  disabled?: boolean
  className?: string
}) {
  if (!source?.favicon_url) return null

  return (
    <Favicon
      src={source.favicon_url}
      label={source.key}
      decoding="async"
      className={`${className}${disabled ? " opacity-40 grayscale" : ""}`}
    />
  )
}

// TODO: Validate
/**
 * Rank a source by the user's source preferences, lowest first.
 *
 * A source the user has not ordered sits wherever they placed "Other", which is
 * also where every source lands when nobody is signed in.
 */
function useSourceRank(): (source: Source | undefined) => number {
  const { data: preferences } = useQuery({
    queryKey: ["source-preferences"],
    queryFn: () => UsersService.readSourcePreferences(),
    enabled: isLoggedIn(),
  })

  const ranks = new Map(
    (preferences ?? []).map((preference, index) => [
      preference.source_key,
      index,
    ]),
  )
  const otherRank = ranks.get(OTHER_SOURCE_KEY) ?? ranks.size

  return (source) => (source && ranks.get(source.key)) ?? otherRank
}

// TODO: Validate
/**
 * Whether the user has turned a source off.
 *
 * A source nobody has an opinion about is on, which is also every source when
 * nobody is signed in.
 */
function useSourceDisabled(): (source: Source | undefined) => boolean {
  const { data: preferences } = useQuery({
    queryKey: ["source-preferences"],
    queryFn: () => UsersService.readSourcePreferences(),
    enabled: isLoggedIn(),
  })

  const disabledKeys = new Set(
    (preferences ?? [])
      .filter((preference) => preference.enabled === false)
      .map((preference) => preference.source_key),
  )

  return (source) => Boolean(source && disabledKeys.has(source.key))
}

// TODO: Validate
/**
 * Group titles that are the same title, keeping the order they arrived in.
 *
 * `tmdb_title_id` names the title itself rather than one service's
 * non-canonical row of it, so it is the whole of the grouping. A non-canonical
 * row that has no title yet stands for itself under its own id, rather than
 * every such row reading as one title.
 */
export function groupTitles(titles: Title[]): Title[][] {
  const groups = new Map<string, Title[]>()
  for (const title of titles) {
    const key = title.tmdb_title_id ?? title.id
    const group = groups.get(key)
    if (group) {
      group.push(title)
    } else {
      groups.set(key, [title])
    }
  }
  return [...groups.values()]
}

// TODO: Validate
/**
 * The title groups a view renders, each ordered by the user's source preferences.
 *
 * @see groupTitles for what counts as the same title.
 */
function useTitleGroups(titles: Title[], sources: Record<string, Source>) {
  const sourceRank = useSourceRank()
  const sourceDisabled = useSourceDisabled()

  // TODO: Validate
  const bySourceRank = (first: Title, second: Title) =>
    sourceRank(sources[first.source_id]) - sourceRank(sources[second.source_id])

  return {
    groups: groupTitles(titles).map((group) => [...group].sort(bySourceRank)),
    isTitleDisabled: (title: Title) => sourceDisabled(sources[title.source_id]),
  }
}

// TODO: Validate
export function TitleCards({
  titles,
  sources,
  tmdbTitles = {},
  tmdbSources = {},
  stats = {},
  details = {},
  renderActions,
  renderExpanded,
  onSelect,
}: {
  titles: Title[]
  sources: Record<string, Source>
  /** The title itself behind each row, keyed by `tmdb_title_id`. */
  tmdbTitles?: Record<string, Title>
  /** The source each title itself was written by, keyed by `tmdb_title_id`. */
  tmdbSources?: Record<string, Source>
  stats?: Record<string, ChannelTitleStats>
  details?: Record<string, TitleCardDetails>
  renderActions?: (group: TitleGroup) => ReactNode
  renderExpanded?: (group: TitleGroup) => ReactNode
  onSelect?: (group: TitleGroup) => void
}) {
  const { groups, isTitleDisabled } = useTitleGroups(titles, sources)

  return (
    <div className="grid items-start gap-3 grid-cols-[repeat(auto-fill,minmax(min(100%,440px),1fr))]">
      {groups.map((group) => {
        const [firstTitle] = group
        const tmdbTitleId = firstTitle.tmdb_title_id ?? firstTitle.id
        const tmdbTitle = tmdbTitles[tmdbTitleId]
        // The title's own name, falling back to a website's for a title nothing
        // catalogued, which is the only name there is to read it under.
        const name = (tmdbTitle ? tmdbTitle.name : firstTitle.name) ?? ""
        const titleGroup: TitleGroup = { tmdbTitleId, name }
        // The title's own artwork, for the same reason as its name: a card is
        // one title, and a website's listing of it is only what is left when
        // nothing catalogued the title or the cataloguer held no image.
        const artwork =
          tmdbTitle?.poster_thumbnail_url ??
          tmdbTitle?.poster_url ??
          tmdbTitle?.thumbnail_url ??
          tmdbTitle?.image_url
        const expanded = renderExpanded?.(titleGroup)
        const actions = renderActions?.(titleGroup)
        // A favicon is how a card names a site, so a listing whose site has none
        // to show reads as nothing at all without a note in its place.
        const streamable = [
          ...new Map(
            group
              .filter((title) => sources[title.source_id]?.favicon_url)
              .map((title) => [title.source_id, title]),
          ).values(),
        ]
        // Who wrote the title down, which is not one of the sites with it:
        // a card is one title, and the row of sites underneath is where it can
        // be watched.
        const tmdbSource = tmdbSources[tmdbTitleId]

        return (
          // A card is one title, and the same listing can be a card under each of
          // the titles it mixes, so the title names the card rather than the
          // non-canonical row.
          <Fragment key={titleGroup.tmdbTitleId}>
            <Card className="relative gap-0 overflow-hidden py-0 hover:border-primary">
              <TitleSummaryLayout
                artwork={artwork}
                artworkAlt={name}
                artworkOverlay={
                  /* Who the title is catalogued by sits over the artwork, apart
                     from the row of sites it can be watched on. */
                  tmdbSource?.favicon_url && (
                    <span className="absolute top-1 left-1 z-10 rounded bg-background/80 p-0.5">
                      <SourceFavicon source={tmdbSource} className="size-5" />
                    </span>
                  )
                }
                title={tmdbTitle}
                stats={stats[tmdbTitleId]}
                details={details[tmdbTitleId]}
                heading={
                  /* The whole card opens the title, since everything on it is
                     about that one title. */
                  <button
                    type="button"
                    className="wrap-break-word text-left font-bold after:absolute after:inset-0"
                    onClick={() => onSelect?.(titleGroup)}
                  >
                    {name}
                    {tmdbTitle?.year ? ` (${tmdbTitle.year})` : ""}
                  </button>
                }
                description={
                  tmdbTitle?.description && (
                    <FilledDescription text={tmdbTitle.description} />
                  )
                }
                footer={
                  <div className="relative z-10 flex w-fit flex-wrap items-center gap-1">
                    {streamable.length > 0 ? (
                      streamable.map((title) => (
                        <SourceFavicon
                          key={title.id}
                          source={sources[title.source_id]}
                          disabled={isTitleDisabled(title)}
                        />
                      ))
                    ) : (
                      <span className="text-muted-foreground text-xs">
                        Not Available to Stream
                      </span>
                    )}
                  </div>
                }
                contentClassName={actions ? "pb-8" : undefined}
              />
              {/* The channel holds the title, so one set of actions covers every
                  site listed above. They sit in the corner rather than in a row
                  of their own, which would leave a gap under a short card. */}
              {actions && (
                <div className="absolute right-1 bottom-1 z-10 rounded bg-background/80">
                  {actions}
                </div>
              )}
            </Card>
            {expanded && (
              <div className="col-span-full rounded-lg border p-4">
                {expanded}
              </div>
            )}
          </Fragment>
        )
      })}
    </div>
  )
}
