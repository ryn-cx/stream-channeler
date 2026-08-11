// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ChevronDown, ChevronRight, ChevronUp } from "lucide-react"
import { useEffect, useState } from "react"
import type {
  WhitelistEpisodeOutput,
  WhitelistSeasonOutput,
  WhitelistShowInput,
  WhitelistSourceOutput,
} from "@/client"
import { ChannelsService } from "@/client"
import { EpisodeInformationPanel } from "@/components/ChannelCommon/EpisodeInformationDialog"
import { SeasonInformationPanel } from "@/components/ChannelCommon/SeasonInformationDialog"
import { ShowInformationPanel } from "@/components/ChannelCommon/ShowInformationDialog"
import { Button } from "@/components/ui/button"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { EpisodeExpiryDialog } from "./EpisodeExpiryDialog"
import { isExpired, isoToLocalInput, localInputToIso } from "./expiry"

// TODO: Validate
/** The favicons of the websites' copies a season or episode was found on. */
function SourceFavicons({
  showIds,
  sourcesByShowId,
}: {
  showIds: string[]
  sourcesByShowId: Map<string, WhitelistSourceOutput>
}) {
  return (
    <span className="flex items-center gap-1 shrink-0">
      {showIds.map((showId) => {
        const source = sourcesByShowId.get(showId)
        if (!source?.favicon_url) return null
        return (
          <Tooltip key={showId}>
            <TooltipTrigger asChild>
              <img
                src={source.favicon_url}
                alt={`${source.source_name} favicon`}
                className="size-6 shrink-0"
              />
            </TooltipTrigger>
            <TooltipContent>
              {source.source_name ?? "Unknown source"}
            </TooltipContent>
          </Tooltip>
        )
      })}
    </span>
  )
}

/**
 * One season row: the stored seasons it stands for, and the episodes under it.
 *
 * A website numbers its own seasons, which is not how TMDB numbers the same
 * ones, so a row stands for a TMDB season rather than a stored one and the
 * stored seasons whose episodes TMDB puts in it are all listed together. A
 * season filter is about a stored season, so a row carries every stored season
 * it covers and marks them together.
 */
interface SeasonGroup {
  key: string
  label: string
  seasons: WhitelistSeasonOutput[]
  episodes: WhitelistEpisodeOutput[]
}

// A name that says nothing the episode's own number does not, whether the site
// wrote it as "Episode 3", "EP 3", or just "3".
const NUMBERED_EPISODE_NAME = /^(?:episode|ep\.?)?\s*0*(\d+)$/i

// TODO: Validate
function tmdbGroupKey(tmdbSeasonNumber: number) {
  return `tmdb-${tmdbSeasonNumber}`
}

// A season TMDB has a record of is one row for every site carrying it, so the
// episodes under it TMDB has no record of would be read as one site's had they
// only their season to go by. They are told apart by the sites carrying them.
// TODO: Validate
function siteGroupKey(seasonId: string, showIds: string[]) {
  return `season-${seasonId}-${[...showIds].sort().join("-")}`
}

// TODO: Validate
function siteSeasonLabel(
  season: WhitelistSeasonOutput,
  anySeasonHasNumber: boolean,
) {
  if (!anySeasonHasNumber) {
    return season.name ?? ""
  }
  const seasonName = season.name ? ` - ${season.name}` : ""
  return `Season ${season.season_number ?? "?"}${seasonName}`
}

// TODO: Validate
function groupSeasons(
  seasons: WhitelistSeasonOutput[],
  episodes: WhitelistEpisodeOutput[],
): SeasonGroup[] {
  const anySeasonHasNumber = seasons.some(
    (season) => season.season_number != null,
  )
  const seasonsById = new Map(seasons.map((season) => [season.id, season]))
  const episodesBySeasonId = new Map<string, WhitelistEpisodeOutput[]>()
  for (const episode of episodes) {
    const seasonEpisodes = episodesBySeasonId.get(episode.season_id) ?? []
    seasonEpisodes.push(episode)
    episodesBySeasonId.set(episode.season_id, seasonEpisodes)
  }

  const groups = new Map<string, SeasonGroup>()
  // TODO: Validate
  const groupFor = (key: string, label: string) => {
    const existing = groups.get(key)
    if (existing) return existing
    const created: SeasonGroup = { key, label, seasons: [], episodes: [] }
    groups.set(key, created)
    return created
  }

  // A stored season belongs wherever its episodes were put, which is what merges
  // the site's split of a TMDB season back into the one row. Its episodes TMDB
  // has no record of are kept out of the rows TMDB numbers, so a season carrying
  // both is listed in each. A season with no episodes at all has only its own
  // TMDB number to go by.
  // TODO: Validate
  const groupKeysOfSeason = (season: WhitelistSeasonOutput) => {
    const seasonEpisodes = episodesBySeasonId.get(season.id) ?? []
    const keys = new Set(
      seasonEpisodes.map((episode) =>
        episode.tmdb_season_number != null
          ? tmdbGroupKey(episode.tmdb_season_number)
          : siteGroupKey(season.id, episode.show_ids),
      ),
    )
    if (keys.size > 0) return [...keys]
    return season.tmdb_season_number != null
      ? [tmdbGroupKey(season.tmdb_season_number)]
      : [siteGroupKey(season.id, season.show_ids)]
  }

  // TODO: Validate
  const labelForKey = (
    key: string,
    season: WhitelistSeasonOutput | undefined,
  ) => {
    if (key.startsWith("tmdb-")) {
      return `Season ${key.replace("tmdb-", "")}`
    }
    return season ? siteSeasonLabel(season, anySeasonHasNumber) : ""
  }

  const keysBySeasonId = new Map(
    seasons.map((season) => [season.id, groupKeysOfSeason(season)]),
  )
  for (const season of seasons) {
    for (const key of keysBySeasonId.get(season.id) ?? []) {
      groupFor(key, labelForKey(key, season)).seasons.push(season)
    }
  }

  for (const episode of episodes) {
    const season = seasonsById.get(episode.season_id)
    // An episode TMDB has no record of is listed apart from the ones it does, so
    // a row TMDB numbers holds only what TMDB put there.
    const ownKey =
      episode.tmdb_season_number != null
        ? tmdbGroupKey(episode.tmdb_season_number)
        : siteGroupKey(episode.season_id, episode.show_ids)
    // An episode several seasons carry is listed once under each of them, which
    // is one entry per season row and one row per season the sites split it into.
    const rowKeys = (keysBySeasonId.get(episode.season_id) ?? []).filter(
      (key) => !key.startsWith("tmdb-"),
    )
    for (const key of new Set(
      episode.tmdb_season_number != null ? [ownKey] : [ownKey, ...rowKeys],
    )) {
      const group = groupFor(key, labelForKey(key, season))
      // The same episode reaches a row from every site carrying it, and it is one
      // entry there naming them all.
      const listed = group.episodes.find(
        (listedEpisode) =>
          listedEpisode.canonical_episode_id === episode.canonical_episode_id,
      )
      if (listed) {
        listed.show_ids = [
          ...new Set([...listed.show_ids, ...episode.show_ids]),
        ]
        continue
      }
      group.episodes.push({ ...episode })
    }
  }

  // The site's split of a TMDB season leaves the episodes of one row numbered by
  // more than one website, so a row TMDB numbers is read in TMDB's order.
  for (const group of groups.values()) {
    if (
      group.episodes.every((episode) => episode.tmdb_episode_number != null)
    ) {
      group.episodes.sort(
        (first, second) =>
          (first.tmdb_episode_number ?? 0) - (second.tmdb_episode_number ?? 0),
      )
    }
    if (!group.key.startsWith("tmdb-")) continue
    // Only a season TMDB has a record of can name a row TMDB numbers. A website
    // that split the season carries its own number in the name of its copy, which
    // is the very number the row is there to replace.
    const name = group.seasons.find(
      (season) => season.tmdb_season_number != null && season.name,
    )?.name
    if (name && name !== group.label) {
      group.label = `${group.label} - ${name}`
    }
  }

  return [...groups.values()]
}

interface WhitelistManagerProps {
  channelId: string
  showId: string
  showName: string
  onClose: () => void
}

// TODO: Validate
export function WhitelistManager({
  channelId,
  showId,
  showName,
  onClose,
}: WhitelistManagerProps) {
  const [isWhitelist, setIsWhitelist] = useState(false)
  // The `Show` ids of the websites' copies that carry a filter entry.
  const [enabledSourceIds, setEnabledSourceIds] = useState<Set<string>>(
    new Set(),
  )
  const [enabledSeasonIds, setEnabledSeasonIds] = useState<Set<string>>(
    new Set(),
  )
  // A filter is about the episode rather than one season's listing of it, so the
  // episodes two seasons share are marked by identifier and move together.
  const [enabledEpisodeIdentifiers, setEnabledEpisodeIdentifiers] = useState<
    Set<string>
  >(new Set())
  // Maps an episode identifier to its expiry as a datetime-local input value.
  // Absent = no expiry.
  const [episodeExpiry, setEpisodeExpiry] = useState<Map<string, string>>(
    new Map(),
  )
  const [expandedSeasons, setExpandedSeasons] = useState<Set<string>>(new Set())
  const [sourcesExpanded, setSourcesExpanded] = useState(true)
  const [seasonsExpanded, setSeasonsExpanded] = useState(true)
  // Episode awaiting the expiry popup before being added to the filter.
  const [pendingEpisode, setPendingEpisode] =
    useState<WhitelistEpisodeOutput | null>(null)
  // The record whose information popup is open, if any.
  const [informationEpisodeId, setInformationEpisodeId] = useState<
    string | null
  >(null)
  const [informationSeasonKey, setInformationSeasonKey] = useState<
    string | null
  >(null)
  const [informationShowId, setInformationShowId] = useState<string | null>(
    null,
  )

  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const { data: whitelistData, isLoading } = useQuery({
    queryKey: ["channelShowWhitelist", channelId, showId],
    queryFn: () => ChannelsService.getChannelWhitelist({ channelId, showId }),
  })

  useEffect(() => {
    if (whitelistData) {
      setIsWhitelist(whitelistData.is_whitelist ?? false)
      setEnabledSourceIds(
        new Set(
          whitelistData.sources
            .filter((source) => source.filtered)
            .map((source) => source.show_id),
        ),
      )
      setEnabledSeasonIds(
        new Set(
          whitelistData.seasons
            .filter((season) => season.filtered)
            .map((season) => season.id),
        ),
      )
      setEnabledEpisodeIdentifiers(
        new Set(
          whitelistData.episodes
            .filter(
              (episode) => episode.filtered && !isExpired(episode.expires_at),
            )
            .map((episode) => episode.canonical_episode_id),
        ),
      )
      setEpisodeExpiry(
        new Map(
          whitelistData.episodes
            .filter(
              (episode) => episode.expires_at && !isExpired(episode.expires_at),
            )
            .map((episode) => [
              episode.canonical_episode_id,
              isoToLocalInput(episode.expires_at),
            ]),
        ),
      )
    }
  }, [whitelistData])

  const saveMutation = useMutation({
    mutationFn: (input: WhitelistShowInput) =>
      ChannelsService.updateChannelWhitelist({
        channelId,
        showId,
        requestBody: input,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["channelShowWhitelist", channelId, showId],
      })
      queryClient.invalidateQueries({ queryKey: ["episodes", channelId] })
      showSuccessToast("Whitelist settings saved successfully")
      onClose()
    },
    onError: handleError.bind(showErrorToast),
  })

  // TODO: Validate
  const toggleIsWhitelist = () => {
    setIsWhitelist(!isWhitelist)
  }

  // TODO: Validate
  const toggleGroupExpanded = (groupKey: string) => {
    const newExpanded = new Set(expandedSeasons)
    if (newExpanded.has(groupKey)) {
      newExpanded.delete(groupKey)
    } else {
      newExpanded.add(groupKey)
    }
    setExpandedSeasons(newExpanded)
  }

  // TODO: Validate
  const toggleSourceEnabled = (showId: string) => {
    const newEnabled = new Set(enabledSourceIds)
    if (newEnabled.has(showId)) {
      newEnabled.delete(showId)
    } else {
      newEnabled.add(showId)
    }
    setEnabledSourceIds(newEnabled)
  }

  // A row can stand for more than one stored season, and they are marked together.
  // TODO: Validate
  const toggleSeasonsEnabled = (seasonIds: string[], enabled: boolean) => {
    const newEnabled = new Set(enabledSeasonIds)
    for (const seasonId of seasonIds) {
      if (enabled) {
        newEnabled.delete(seasonId)
      } else {
        newEnabled.add(seasonId)
      }
    }
    setEnabledSeasonIds(newEnabled)
  }

  // TODO: Validate
  const toggleEpisodeEnabled = (episodeIdentifier: string) => {
    const newEnabled = new Set(enabledEpisodeIdentifiers)
    if (newEnabled.has(episodeIdentifier)) {
      newEnabled.delete(episodeIdentifier)
    } else {
      newEnabled.add(episodeIdentifier)
    }
    setEnabledEpisodeIdentifiers(newEnabled)
  }

  // TODO: Validate
  const setEpisodeExpiryValue = (episodeIdentifier: string, value: string) => {
    setEpisodeExpiry((previous) => {
      const next = new Map(previous)
      if (value) {
        next.set(episodeIdentifier, value)
      } else {
        next.delete(episodeIdentifier)
      }
      return next
    })
  }

  // Clicking an episode toggles it; removing is immediate, adding first asks for the
  // optional expiry via a popup.
  // TODO: Validate
  const handleEpisodeClick = (episode: WhitelistEpisodeOutput) => {
    if (enabledEpisodeIdentifiers.has(episode.canonical_episode_id)) {
      toggleEpisodeEnabled(episode.canonical_episode_id)
    } else {
      setPendingEpisode(episode)
    }
  }

  // TODO: Validate
  const confirmEpisodeExpiry = (expiresAtLocal: string) => {
    if (!pendingEpisode) return
    setEnabledEpisodeIdentifiers((previous) =>
      new Set(previous).add(pendingEpisode.canonical_episode_id),
    )
    setEpisodeExpiryValue(pendingEpisode.canonical_episode_id, expiresAtLocal)
    setPendingEpisode(null)
  }

  // TODO: Validate
  const handleSave = () => {
    if (!whitelistData) return

    const input: WhitelistShowInput = {
      is_whitelist: isWhitelist,
      sources: whitelistData.sources
        .filter((source) => !source.is_tmdb)
        .map((source) => ({
          id: source.show_id,
          marked: enabledSourceIds.has(source.show_id),
        })),
      seasons: whitelistData.seasons.map((season) => ({
        id: season.id,
        marked: enabledSeasonIds.has(season.id),
      })),
      episodes: whitelistData.episodes.map((episode) => ({
        id: episode.id,
        marked: enabledEpisodeIdentifiers.has(episode.canonical_episode_id),
        expires_at: enabledEpisodeIdentifiers.has(episode.canonical_episode_id)
          ? localInputToIso(
              episodeExpiry.get(episode.canonical_episode_id) ?? "",
            )
          : null,
      })),
    }
    saveMutation.mutate(input)
  }

  // TODO: Validate
  const getEpisodeLabel = (episode: WhitelistEpisodeOutput) => {
    const episodeName = episode.name ?? ""
    const episodeNumber = episode.tmdb_episode_number ?? episode.sort_order
    if (episodeNumber == null) {
      return episodeName
    }
    // A website that never named an episode calls it by its number, which the
    // label already says, so "Episode 3 - Episode 3" is read as "Episode 3".
    const nameIsNumber = NUMBERED_EPISODE_NAME.exec(episodeName)
    const named = episodeName && Number(nameIsNumber?.[1]) !== episodeNumber
    return `Episode ${episodeNumber}${named ? ` - ${episodeName}` : ""}`
  }

  // TODO: Validate
  const getSeasonActionLabel = (enabled: boolean) => {
    if (isWhitelist) {
      return enabled ? "Remove from Whitelist" : "Add to Whitelist"
    }
    return enabled ? "Remove from Blacklist" : "Add to Blacklist"
  }

  // A source entry reads the same way a season entry does: in whitelist mode it is
  // one of the sites the show is watched on, in blacklist mode one of the sites it
  // is skipped on.
  const getSourceActionLabel = getSeasonActionLabel

  // TODO: Validate
  const getEpisodeActionLabel = (
    episodeEnabled: boolean,
    seasonEnabled: boolean,
  ) => {
    // When the season itself is filtered, an episode-level entry inverts that filter
    // for the episode (a blacklisted season's marked episode is shown again; a
    // whitelisted season's marked episode is excluded), so the add/remove wording flips.
    if (isWhitelist) {
      if (seasonEnabled) {
        return episodeEnabled ? "Add to Whitelist" : "Remove from Whitelist"
      }
      return episodeEnabled ? "Remove from Whitelist" : "Add to Whitelist"
    }
    if (seasonEnabled) {
      return episodeEnabled ? "Add to Blacklist" : "Remove from Blacklist"
    }
    return episodeEnabled ? "Remove from Blacklist" : "Add to Blacklist"
  }

  if (!whitelistData) return
  const sourcesByShowId = new Map(
    whitelistData.sources.map((source) => [source.show_id, source]),
  )
  // TMDB catalogues the media rather than carrying it, so it never stands for a
  // site an episode can be watched on.
  const tmdbShowIds = new Set(
    whitelistData.sources
      .filter((source) => source.is_tmdb)
      .map((source) => source.show_id),
  )
  // TODO: Validate
  const watchableShowIds = (showIds: string[]) =>
    showIds.filter((showId) => !tmdbShowIds.has(showId))
  const watchableSources = whitelistData.sources.filter(
    (source) => !source.is_tmdb,
  )
  // A row's sites are the ones carrying the episodes it lists, since a stored
  // season can be a shell a site announced and never filled. TMDB is among them
  // wherever an episode has a TMDB id, and stands on its own season record when
  // the row has no episodes at all.
  // TODO: Validate
  const seasonShowIds = (group: SeasonGroup) => {
    if (group.episodes.length > 0) {
      return [...new Set(group.episodes.flatMap((episode) => episode.show_ids))]
    }
    return [
      ...new Set(
        group.seasons
          .flatMap((season) => season.show_ids)
          .filter((showId) => tmdbShowIds.has(showId)),
      ),
    ]
  }
  const seasonGroups = groupSeasons(
    whitelistData.seasons,
    whitelistData.episodes,
  )
  // TODO: Validate
  const isGroupEnabled = (group: SeasonGroup) =>
    group.seasons.length > 0 &&
    group.seasons.every((season) => enabledSeasonIds.has(season.id))
  // The row an episode is listed under decides how its own entry reads, so its
  // row's state is looked up rather than the season it was imported under.
  const groupEnabledByEpisodeId = new Map(
    seasonGroups.flatMap((group) =>
      group.episodes.map(
        (episode) => [episode.id, isGroupEnabled(group)] as const,
      ),
    ),
  )

  return (
    <>
      <div className="flex flex-col gap-4">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold">
              Manage Whitelist - {showName}
            </h2>
            <p className="text-sm text-muted-foreground">
              {isWhitelist
                ? "Only selected sites, seasons and episodes will appear. New episodes are not automatically added."
                : "All episodes are shown by default. New episodes are automatically added."}
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <ChevronUp className="h-4 w-4 mr-1" /> Collapse
          </Button>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <p className="text-sm text-muted-foreground">Loading...</p>
          </div>
        ) : (
          <>
            <div className="flex flex-col gap-4">
              <div className="flex flex-wrap items-center justify-between gap-2 p-4 border rounded bg-muted/50 shrink-0">
                <div>
                  <h3 className="font-semibold">
                    Current Mode:{" "}
                    {isWhitelist ? "Whitelist Mode" : "Blacklist Mode"}
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    {isWhitelist
                      ? "Only whitelisted episodes will be shown"
                      : "All episodes except blacklisted ones will be shown"}
                  </p>
                </div>
                <Button onClick={toggleIsWhitelist} variant="outline">
                  Switch to {isWhitelist ? "Blacklist" : "Whitelist"} Mode
                </Button>
              </div>

              <div className="border rounded shrink-0">
                <div className="flex items-center gap-2 p-3 bg-accent/50">
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => setSourcesExpanded(!sourcesExpanded)}
                  >
                    {sourcesExpanded ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                  </Button>
                  <div className="flex-1">
                    <h3 className="font-medium">Sources</h3>
                    <p className="text-sm text-muted-foreground">
                      {isWhitelist
                        ? "Only whitelisted sites are watched for this show. Whitelisting none watches them all."
                        : "All sites are watched except blacklisted ones"}
                    </p>
                  </div>
                </div>
                {sourcesExpanded && (
                  <div className="p-2 space-y-1 border-t">
                    {watchableSources.length === 0 ? (
                      <p className="text-sm text-muted-foreground text-center py-4">
                        No sources found for this show
                      </p>
                    ) : (
                      watchableSources.map((source) => {
                        const sourceEnabled = enabledSourceIds.has(
                          source.show_id,
                        )
                        return (
                          <div key={source.show_id}>
                            <div className="flex items-center gap-2 p-2 hover:bg-accent/30 rounded">
                              {source.favicon_url && (
                                <img
                                  src={source.favicon_url}
                                  alt=""
                                  className="size-6 shrink-0"
                                />
                              )}
                              <button
                                type="button"
                                className="flex-1 text-left text-sm hover:underline"
                                onClick={() =>
                                  setInformationShowId(
                                    informationShowId === source.show_id
                                      ? null
                                      : source.show_id,
                                  )
                                }
                              >
                                {source.source_name ?? "Unknown source"}
                              </button>
                              <Button
                                variant={sourceEnabled ? "default" : "outline"}
                                size="sm"
                                onClick={() =>
                                  toggleSourceEnabled(source.show_id)
                                }
                              >
                                {getSourceActionLabel(sourceEnabled)}
                              </Button>
                            </div>
                            {informationShowId === source.show_id && (
                              <div className="rounded border bg-muted/30 p-4">
                                <ShowInformationPanel showId={source.show_id} />
                              </div>
                            )}
                          </div>
                        )
                      })
                    )}
                  </div>
                )}
              </div>

              <div className="border rounded shrink-0">
                <div className="flex items-center gap-2 p-3 bg-accent/50">
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => setSeasonsExpanded(!seasonsExpanded)}
                  >
                    {seasonsExpanded ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                  </Button>
                  <div className="flex-1">
                    <h3 className="font-medium">Seasons</h3>
                    <p className="text-sm text-muted-foreground">
                      {isWhitelist
                        ? "Only whitelisted seasons and episodes will appear"
                        : "All seasons are shown except blacklisted ones"}
                    </p>
                  </div>
                </div>
                {seasonsExpanded && (
                  <div className="p-2 space-y-1 border-t">
                    {seasonGroups.length === 0 ? (
                      <p className="text-sm text-muted-foreground text-center py-4">
                        No seasons found for this show
                      </p>
                    ) : (
                      seasonGroups.map((group) => {
                        const seasonEnabled = isGroupEnabled(group)
                        const rowShowIds = seasonShowIds(group)
                        const tmdbRowShowIds = rowShowIds.filter((showId) =>
                          tmdbShowIds.has(showId),
                        )
                        // TMDB leads the row, and the sites stand in front of the
                        // name only when TMDB has no record of the season to lead it.
                        const leadingShowIds =
                          tmdbRowShowIds.length > 0
                            ? tmdbRowShowIds
                            : rowShowIds
                        const trailingShowIds =
                          tmdbRowShowIds.length > 0
                            ? rowShowIds.filter(
                                (showId) => !tmdbShowIds.has(showId),
                              )
                            : []
                        return (
                          <div key={group.key}>
                            <div className="flex items-center gap-2 p-2 hover:bg-accent/30 rounded">
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                onClick={() => toggleGroupExpanded(group.key)}
                              >
                                {expandedSeasons.has(group.key) ? (
                                  <ChevronDown className="h-4 w-4" />
                                ) : (
                                  <ChevronRight className="h-4 w-4" />
                                )}
                              </Button>
                              {leadingShowIds.length > 0 && (
                                <SourceFavicons
                                  showIds={leadingShowIds}
                                  sourcesByShowId={sourcesByShowId}
                                />
                              )}
                              <button
                                type="button"
                                className="flex-1 text-left text-sm hover:underline"
                                onClick={() =>
                                  setInformationSeasonKey(
                                    informationSeasonKey === group.key
                                      ? null
                                      : group.key,
                                  )
                                }
                              >
                                {group.label}
                              </button>
                              {trailingShowIds.length > 0 && (
                                <SourceFavicons
                                  showIds={trailingShowIds}
                                  sourcesByShowId={sourcesByShowId}
                                />
                              )}
                              <Button
                                variant={seasonEnabled ? "default" : "outline"}
                                size="sm"
                                onClick={() =>
                                  toggleSeasonsEnabled(
                                    group.seasons.map((season) => season.id),
                                    seasonEnabled,
                                  )
                                }
                              >
                                {getSeasonActionLabel(seasonEnabled)}
                              </Button>
                            </div>

                            {informationSeasonKey === group.key && (
                              <div className="ml-8 rounded border bg-muted/30 p-4">
                                <SeasonInformationPanel
                                  seasonIds={group.seasons.map(
                                    (season) => season.id,
                                  )}
                                />
                              </div>
                            )}

                            {expandedSeasons.has(group.key) && (
                              <div className="p-2 space-y-1">
                                {group.episodes.length === 0 ? (
                                  <p className="text-sm text-muted-foreground text-center py-2">
                                    No episodes found
                                  </p>
                                ) : (
                                  group.episodes.map((episode) => {
                                    const episodeEnabled =
                                      enabledEpisodeIdentifiers.has(
                                        episode.canonical_episode_id,
                                      )
                                    return (
                                      <div key={episode.id}>
                                        <div className="flex items-center gap-2 p-2 hover:bg-accent/30 rounded">
                                          <button
                                            type="button"
                                            className="flex-1 text-left text-sm ml-8 hover:underline"
                                            onClick={() =>
                                              setInformationEpisodeId(
                                                informationEpisodeId ===
                                                  episode.id
                                                  ? null
                                                  : episode.id,
                                              )
                                            }
                                          >
                                            {getEpisodeLabel(episode)}
                                            {episodeEnabled &&
                                              episodeExpiry.get(
                                                episode.canonical_episode_id,
                                              ) && (
                                                <span className="ml-2 text-xs text-muted-foreground">
                                                  (until{" "}
                                                  {new Date(
                                                    episodeExpiry.get(
                                                      episode.canonical_episode_id,
                                                    )!,
                                                  ).toLocaleString()}
                                                  )
                                                </span>
                                              )}
                                          </button>
                                          <SourceFavicons
                                            showIds={watchableShowIds(
                                              episode.show_ids,
                                            )}
                                            sourcesByShowId={sourcesByShowId}
                                          />
                                          <Button
                                            variant={
                                              episodeEnabled !== seasonEnabled
                                                ? "default"
                                                : "outline"
                                            }
                                            size="sm"
                                            onClick={() =>
                                              handleEpisodeClick(episode)
                                            }
                                          >
                                            {getEpisodeActionLabel(
                                              episodeEnabled,
                                              seasonEnabled,
                                            )}
                                          </Button>
                                        </div>
                                        {informationEpisodeId ===
                                          episode.id && (
                                          <div className="ml-8 rounded border bg-muted/30 p-4">
                                            <EpisodeInformationPanel
                                              episodeId={episode.id}
                                            />
                                          </div>
                                        )}
                                      </div>
                                    )
                                  })
                                )}
                              </div>
                            )}
                          </div>
                        )
                      })
                    )}
                  </div>
                )}
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={onClose}
                disabled={saveMutation.isPending}
              >
                Cancel
              </Button>
              <LoadingButton
                onClick={handleSave}
                loading={saveMutation.isPending}
              >
                Save Changes
              </LoadingButton>
            </div>
          </>
        )}
      </div>

      {pendingEpisode && (
        <EpisodeExpiryDialog
          open={!!pendingEpisode}
          // The popup only opens when adding an episode-level entry, so the action
          // matches the not-yet-enabled label (which already accounts for the season).
          title={getEpisodeActionLabel(
            false,
            groupEnabledByEpisodeId.get(pendingEpisode.id) ?? false,
          )}
          description={getEpisodeLabel(pendingEpisode)}
          dateLabel="Expires at (optional)"
          confirmLabel={getEpisodeActionLabel(
            false,
            groupEnabledByEpisodeId.get(pendingEpisode.id) ?? false,
          )}
          initialExpiry={
            episodeExpiry.get(pendingEpisode.canonical_episode_id) ?? ""
          }
          onConfirm={confirmEpisodeExpiry}
          onOpenChange={(open) => {
            if (!open) setPendingEpisode(null)
          }}
        />
      )}
    </>
  )
}
