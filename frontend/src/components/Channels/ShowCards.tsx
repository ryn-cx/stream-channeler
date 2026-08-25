// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { Fragment, type ReactNode } from "react"
import type { ChannelShowStats } from "@/client"
import { UsersService } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { isLoggedIn } from "@/hooks/useAuth"

export interface Show {
  id: string
  name?: string | null
  source_id: string
  url?: string | null
  media_type?: string | null
  tmdb_id?: number | null
  canonical_show_id?: string | null
  image_url?: string | null
  year?: number | null
}

export interface Source {
  key: string
  favicon_url?: string | null
  name?: string | null
}

// One card: the title, and every website's row standing for it. The title is
// what a card's actions are about, so it is named by `canonicalShowId` rather
// than by any of the rows, which a website that files two titles under one page
// leaves standing for both.
export interface ShowGroup {
  canonicalShowId: string
  name: string
}

const OTHER_SOURCE_KEY = "Other"

// TODO: Validate
/** The source's favicon, naming the source when it is hovered. */
function SourceFavicon({
  source,
  disabled,
}: {
  source: Source | undefined
  disabled?: boolean
}) {
  if (!source?.favicon_url) return null

  const favicon = (
    <img
      loading="lazy"
      decoding="async"
      src={source.favicon_url}
      alt={`${source.name} favicon`}
      className={`size-8 shrink-0${disabled ? " opacity-40 grayscale" : ""}`}
    />
  )
  if (!source.name) return favicon

  return (
    <Tooltip>
      <TooltipTrigger asChild>{favicon}</TooltipTrigger>
      <TooltipContent>{source.name}</TooltipContent>
    </Tooltip>
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
 * Group shows that are the same title, keeping the order they arrived in.
 *
 * `canonical_show_id` names the title itself rather than one service's
 * non-canonical row of it, so it is the whole of the grouping. A non-canonical
 * row that has no title yet stands for itself under its own id, rather than
 * every such row reading as one title.
 */
export function groupShows(shows: Show[]): Show[][] {
  const groups = new Map<string, Show[]>()
  for (const show of shows) {
    const key = show.canonical_show_id ?? show.id
    const group = groups.get(key)
    if (group) {
      group.push(show)
    } else {
      groups.set(key, [show])
    }
  }
  return [...groups.values()]
}

// TODO: Validate
/**
 * The show groups a view renders, each ordered by the user's source preferences.
 *
 * @see groupShows for what counts as the same show.
 */
function useShowGroups(shows: Show[], sources: Record<string, Source>) {
  const sourceRank = useSourceRank()
  const sourceDisabled = useSourceDisabled()

  // TODO: Validate
  const bySourceRank = (first: Show, second: Show) =>
    sourceRank(sources[first.source_id]) - sourceRank(sources[second.source_id])

  return {
    groups: groupShows(shows).map((group) => [...group].sort(bySourceRank)),
    isShowDisabled: (show: Show) => sourceDisabled(sources[show.source_id]),
  }
}

// TODO: Validate
/**
 * What is known about a title from the channel's own listing of it.
 *
 * The listing carries the title's own account of itself, so a card reads that
 * and leaves the rest to the information panel. What a title is, is the title's
 * own to say rather than any one website's, so a title nothing catalogued has
 * nothing to say here.
 */
function showFacts(
  canonicalShow: Show | undefined,
  stats: ChannelShowStats | undefined,
): string[] {
  const facts = [canonicalShow?.media_type ?? "Not linked to TMDB"]
  // A movie is one episode of one season by construction, so counting them says
  // nothing the "Movie" note has not already said.
  const countsAreImplied =
    canonicalShow?.media_type === "Movie" &&
    stats?.season_count === 1 &&
    stats?.episode_count === 1
  if (countsAreImplied) {
    return facts
  }
  if (stats?.season_count) {
    const seasonCount = stats.season_count
    facts.push(`${seasonCount} ${seasonCount === 1 ? "season" : "seasons"}`)
  }
  if (stats?.episode_count) {
    const episodeCount = stats.episode_count
    facts.push(`${episodeCount} ${episodeCount === 1 ? "episode" : "episodes"}`)
  }
  return facts
}

// TODO: Validate
/**
 * Shows laid out as cards with their artwork, the same show on several services
 * collapsed into one card.
 *
 * A card is read at a glance rather than field by field, so the sites carrying
 * the title are their favicons and the few facts the listing knows sit under the
 * name.
 */
export function ShowCards({
  shows,
  sources,
  canonicalShows = {},
  canonicalSources = {},
  stats = {},
  renderActions,
  renderExpanded,
  onSelect,
}: {
  shows: Show[]
  sources: Record<string, Source>
  /** The title itself behind each row, keyed by `canonical_show_id`. */
  canonicalShows?: Record<string, Show>
  /** The source each title itself was written by, keyed by `canonical_show_id`. */
  canonicalSources?: Record<string, Source>
  stats?: Record<string, ChannelShowStats>
  renderActions?: (group: ShowGroup) => ReactNode
  renderExpanded?: (group: ShowGroup) => ReactNode
  onSelect?: (group: ShowGroup) => void
}) {
  const { groups, isShowDisabled } = useShowGroups(shows, sources)

  return (
    <div className="grid items-start gap-3 grid-cols-[repeat(auto-fill,minmax(220px,1fr))]">
      {groups.map((group) => {
        const [firstShow] = group
        const canonicalShowId = firstShow.canonical_show_id ?? firstShow.id
        const canonicalShow = canonicalShows[canonicalShowId]
        // The title's own name, falling back to a website's for a title nothing
        // catalogued, which is the only name there is to read it under.
        const name = (canonicalShow ? canonicalShow.name : firstShow.name) ?? ""
        const showGroup: ShowGroup = { canonicalShowId, name }
        // The title's own artwork, for the same reason as its name: a card is
        // one title, and a website's listing of it is only what is left when
        // nothing catalogued the title or the cataloguer held no image.
        const artwork = canonicalShow?.image_url
        const expanded = renderExpanded?.(showGroup)
        const actions = renderActions?.(showGroup)
        // A favicon is how a card names a site, so a listing whose site has none
        // to show reads as nothing at all without a note in its place.
        const streamable = group.filter(
          (show) => sources[show.source_id]?.favicon_url,
        )
        // Who wrote the title down, which is not one of the sites carrying it:
        // a card is one title, and the row of sites underneath is where it can
        // be watched.
        const canonicalSource = canonicalSources[canonicalShowId]

        return (
          // A card is one title, and the same listing can be a card under each of
          // the titles it mixes, so the title names the card rather than the
          // non-canonical row.
          <Fragment key={showGroup.canonicalShowId}>
            <Card className="relative gap-0 overflow-hidden py-0 hover:border-primary">
              {/* The whole card opens the title, since everything on it is about
                  that one title. */}
              <button
                type="button"
                className="block w-full text-left"
                onClick={() => onSelect?.(showGroup)}
              >
                <div className="relative aspect-video w-full bg-muted">
                  {artwork && (
                    <img
                      loading="lazy"
                      decoding="async"
                      src={artwork}
                      alt={name}
                      className="size-full object-cover"
                    />
                  )}
                  {/* Who the title is catalogued by sits over the artwork, apart
                      from the row of sites it can be watched on. */}
                  {canonicalSource?.favicon_url && (
                    <span className="absolute top-1 left-1 rounded bg-background/80 p-0.5">
                      <SourceFavicon source={canonicalSource} />
                    </span>
                  )}
                </div>
                <div className="flex flex-col gap-2 p-3">
                  <span className="wrap-break-word text-sm">
                    <span className="font-bold">{name}</span>
                    {canonicalShow?.year ? ` (${canonicalShow.year})` : ""}
                  </span>
                  <div className="flex flex-wrap items-center gap-1">
                    {showFacts(canonicalShow, stats[canonicalShowId]).map(
                      (fact) => (
                        <Badge key={fact} variant="secondary">
                          {fact}
                        </Badge>
                      ),
                    )}
                  </div>
                  <div
                    className={`flex flex-wrap items-center gap-1${actions ? " pr-8" : ""}`}
                  >
                    {streamable.length > 0 ? (
                      streamable.map((show) => (
                        <SourceFavicon
                          key={show.id}
                          source={sources[show.source_id]}
                          disabled={isShowDisabled(show)}
                        />
                      ))
                    ) : (
                      <span className="text-muted-foreground text-xs">
                        Not Available to Stream
                      </span>
                    )}
                  </div>
                </div>
              </button>
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
