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
}

export interface Source {
  key: string
  favicon_url?: string | null
  name?: string | null
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
 * `canonical_show_id` names the title itself rather than one service's copy of
 * it, so it is the whole of the grouping. A copy that has no title yet stands
 * for itself under its own id, rather than every such copy reading as one title.
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
 * and leaves the rest to the information panel.
 */
function showFacts(
  group: Show[],
  stats: ChannelShowStats | undefined,
): string[] {
  const [firstShow] = group
  const facts = [firstShow.media_type ?? "Not linked to TMDB"]
  if (stats?.first_release_date) {
    // Read off the stored date rather than the reader's own clock, which would
    // move a release just after midnight into the year before it.
    facts.push(stats.first_release_date.slice(0, 4))
  }
  // A movie is one episode of one season by construction, so counting them says
  // nothing the "Movie" note has not already said.
  const countsAreImplied =
    firstShow.media_type === "Movie" &&
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
  stats = {},
  renderActions,
  renderExpanded,
  onSelect,
}: {
  shows: Show[]
  sources: Record<string, Source>
  stats?: Record<string, ChannelShowStats>
  renderActions?: (show: Show) => ReactNode
  renderExpanded?: (show: Show) => ReactNode
  onSelect?: (show: Show) => void
}) {
  const { groups, isShowDisabled } = useShowGroups(shows, sources)

  return (
    <div className="grid items-start gap-3 grid-cols-[repeat(auto-fill,minmax(220px,1fr))]">
      {groups.map((group) => {
        const [firstShow] = group
        const name = firstShow.name ?? ""
        const artwork = group.find((show) => show.image_url)?.image_url
        const expanded = renderExpanded?.(firstShow)
        const actions = renderActions?.(firstShow)
        // A favicon is how a card names a site, so a listing whose site has none
        // to show reads as nothing at all without a note in its place.
        const streamable = group.filter(
          (show) => sources[show.source_id]?.favicon_url,
        )

        return (
          <Fragment key={firstShow.id}>
            <Card className="relative gap-0 overflow-hidden py-0 hover:border-primary">
              {/* The whole card opens the title, since everything on it is about
                  that one title. */}
              <button
                type="button"
                className="block w-full text-left"
                onClick={() => onSelect?.(firstShow)}
              >
                <div className="relative aspect-video w-full bg-muted">
                  {artwork && (
                    <img
                      src={artwork}
                      alt={name}
                      className="size-full object-cover"
                    />
                  )}
                  {/* The name reads over the artwork so the card stays as short
                      as the picture it shows. */}
                  <span className="absolute inset-x-0 bottom-0 wrap-break-word bg-linear-to-t from-black/80 to-transparent p-2 text-sm font-medium text-white">
                    {name}
                  </span>
                </div>
                <div className="flex flex-col gap-2 p-3">
                  <div className="flex flex-wrap items-center gap-1">
                    {showFacts(
                      group,
                      firstShow.canonical_show_id
                        ? stats[firstShow.canonical_show_id]
                        : undefined,
                    ).map((fact) => (
                      <Badge key={fact} variant="secondary">
                        {fact}
                      </Badge>
                    ))}
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
