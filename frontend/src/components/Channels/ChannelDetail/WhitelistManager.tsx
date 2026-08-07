// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ChevronDown, ChevronRight } from "lucide-react"
import { useEffect, useState } from "react"
import type {
  WhitelistEpisodeOutput,
  WhitelistSeasonOutput,
  WhitelistShowInput,
  WhitelistSourceOutput,
} from "@/client"
import { ChannelsService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
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
                className="size-4 shrink-0"
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

function tmdbGroupKey(tmdbSeasonNumber: number) {
  return `tmdb-${tmdbSeasonNumber}`
}

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
  const groupFor = (key: string, label: string) => {
    const existing = groups.get(key)
    if (existing) return existing
    const created: SeasonGroup = { key, label, seasons: [], episodes: [] }
    groups.set(key, created)
    return created
  }

  // A stored season with no TMDB season of its own belongs wherever its episodes
  // were put, which is what merges the site's split of a TMDB season back into
  // the one row.
  const groupKeysOfSeason = (season: WhitelistSeasonOutput) => {
    if (season.tmdb_season_number != null) {
      return [tmdbGroupKey(season.tmdb_season_number)]
    }
    const keys = new Set(
      (episodesBySeasonId.get(season.id) ?? [])
        .filter((episode) => episode.tmdb_season_number != null)
        .map((episode) => tmdbGroupKey(episode.tmdb_season_number as number)),
    )
    return keys.size > 0 ? [...keys] : [`season-${season.id}`]
  }

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
    const tmdbSeasonNumber =
      episode.tmdb_season_number ?? season?.tmdb_season_number
    // An episode TMDB has no record of belongs wherever its stored season went,
    // so it is not left in a row of its own under the number the website gave it.
    const key =
      tmdbSeasonNumber != null
        ? tmdbGroupKey(tmdbSeasonNumber)
        : (keysBySeasonId.get(episode.season_id)?.[0] ??
          `season-${episode.season_id}`)
    groupFor(key, labelForKey(key, season)).episodes.push(episode)
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
  isOpen: boolean
  onClose: () => void
}

export function WhitelistManager({
  channelId,
  showId,
  showName,
  isOpen,
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
  const [enabledEpisodeIds, setEnabledEpisodeIds] = useState<Set<string>>(
    new Set(),
  )
  // Maps an episode id to its expiry as a datetime-local input value. Absent = no expiry.
  const [episodeExpiry, setEpisodeExpiry] = useState<Map<string, string>>(
    new Map(),
  )
  const [expandedSeasons, setExpandedSeasons] = useState<Set<string>>(new Set())
  // Episode awaiting the expiry popup before being added to the filter.
  const [pendingEpisode, setPendingEpisode] =
    useState<WhitelistEpisodeOutput | null>(null)

  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const { data: whitelistData, isLoading } = useQuery({
    queryKey: ["channelShowWhitelist", channelId, showId],
    queryFn: () => ChannelsService.getChannelWhitelist({ channelId, showId }),
    enabled: isOpen,
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
      setEnabledEpisodeIds(
        new Set(
          whitelistData.episodes
            .filter(
              (episode) => episode.filtered && !isExpired(episode.expires_at),
            )
            .map((episode) => episode.id),
        ),
      )
      setEpisodeExpiry(
        new Map(
          whitelistData.episodes
            .filter(
              (episode) => episode.expires_at && !isExpired(episode.expires_at),
            )
            .map((episode) => [
              episode.id,
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

  const toggleIsWhitelist = () => {
    setIsWhitelist(!isWhitelist)
  }

  const toggleGroupExpanded = (groupKey: string) => {
    const newExpanded = new Set(expandedSeasons)
    if (newExpanded.has(groupKey)) {
      newExpanded.delete(groupKey)
    } else {
      newExpanded.add(groupKey)
    }
    setExpandedSeasons(newExpanded)
  }

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

  const toggleEpisodeEnabled = (episodeId: string) => {
    const newEnabled = new Set(enabledEpisodeIds)
    if (newEnabled.has(episodeId)) {
      newEnabled.delete(episodeId)
    } else {
      newEnabled.add(episodeId)
    }
    setEnabledEpisodeIds(newEnabled)
  }

  const setEpisodeExpiryValue = (episodeId: string, value: string) => {
    setEpisodeExpiry((previous) => {
      const next = new Map(previous)
      if (value) {
        next.set(episodeId, value)
      } else {
        next.delete(episodeId)
      }
      return next
    })
  }

  // Clicking an episode toggles it; removing is immediate, adding first asks for the
  // optional expiry via a popup.
  const handleEpisodeClick = (episode: WhitelistEpisodeOutput) => {
    if (enabledEpisodeIds.has(episode.id)) {
      toggleEpisodeEnabled(episode.id)
    } else {
      setPendingEpisode(episode)
    }
  }

  const confirmEpisodeExpiry = (expiresAtLocal: string) => {
    if (!pendingEpisode) return
    setEnabledEpisodeIds((previous) => new Set(previous).add(pendingEpisode.id))
    setEpisodeExpiryValue(pendingEpisode.id, expiresAtLocal)
    setPendingEpisode(null)
  }

  const handleSave = () => {
    if (!whitelistData) return

    const input: WhitelistShowInput = {
      is_whitelist: isWhitelist,
      sources: whitelistData.sources.map((source) => ({
        id: source.show_id,
        marked: enabledSourceIds.has(source.show_id),
      })),
      seasons: whitelistData.seasons.map((season) => ({
        id: season.id,
        marked: enabledSeasonIds.has(season.id),
      })),
      episodes: whitelistData.episodes.map((episode) => ({
        id: episode.id,
        marked: enabledEpisodeIds.has(episode.id),
        expires_at: enabledEpisodeIds.has(episode.id)
          ? localInputToIso(episodeExpiry.get(episode.id) ?? "")
          : null,
      })),
    }
    saveMutation.mutate(input)
  }

  const getEpisodeLabel = (episode: WhitelistEpisodeOutput) => {
    const episodeName = episode.name ? ` - ${episode.name}` : ""
    const episodeNumber =
      episode.tmdb_episode_number ?? episode.sort_order ?? "?"
    return `Episode ${episodeNumber}${episodeName}`
  }

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
  const seasonGroups = groupSeasons(
    whitelistData.seasons,
    whitelistData.episodes,
  )
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
      <Dialog open={isOpen} onOpenChange={onClose}>
        <DialogContent className="sm:max-w-3xl max-h-[80vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>Manage Whitelist - {showName}</DialogTitle>
            <DialogDescription>
              {isWhitelist
                ? "Only selected sites, seasons and episodes will appear. New episodes are not automatically added."
                : "All episodes are shown by default. New episodes are automatically added."}
            </DialogDescription>
          </DialogHeader>

          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <p className="text-sm text-muted-foreground">Loading...</p>
            </div>
          ) : (
            <>
              <DialogBody className="flex flex-col gap-4 py-4">
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

                {whitelistData.sources.length > 1 && (
                  <div className="border rounded shrink-0">
                    <div className="p-3 bg-accent/50 border-b">
                      <h3 className="font-medium">Sources</h3>
                      <p className="text-sm text-muted-foreground">
                        {isWhitelist
                          ? "Only whitelisted sites are watched for this show. Whitelisting none watches them all."
                          : "All sites are watched except blacklisted ones"}
                      </p>
                    </div>
                    <div className="p-2 space-y-1">
                      {whitelistData.sources.map((source) => {
                        const sourceEnabled = enabledSourceIds.has(
                          source.show_id,
                        )
                        return (
                          <div
                            key={source.show_id}
                            className="flex items-center gap-2 p-2 hover:bg-accent/30 rounded"
                          >
                            {source.favicon_url && (
                              <img
                                src={source.favicon_url}
                                alt=""
                                className="size-4 shrink-0"
                              />
                            )}
                            <span className="flex-1 text-sm">
                              {source.source_name ?? "Unknown source"}
                            </span>
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
                        )
                      })}
                    </div>
                  </div>
                )}

                <div className="border rounded">
                  <div className="p-4 space-y-2">
                    {seasonGroups.length === 0 ? (
                      <p className="text-sm text-muted-foreground text-center py-4">
                        No seasons found for this show
                      </p>
                    ) : (
                      seasonGroups.map((group) => {
                        const seasonEnabled = isGroupEnabled(group)
                        return (
                          <div key={group.key} className="border rounded">
                            <div className="flex items-center gap-2 p-3 bg-accent/50">
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
                              <span className="flex-1 font-medium">
                                {group.label}
                              </span>
                              <SourceFavicons
                                showIds={[
                                  ...new Set(
                                    group.seasons.flatMap(
                                      (season) => season.show_ids,
                                    ),
                                  ),
                                ]}
                                sourcesByShowId={sourcesByShowId}
                              />
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

                            {expandedSeasons.has(group.key) && (
                              <div className="p-2 space-y-1">
                                {group.episodes.length === 0 ? (
                                  <p className="text-sm text-muted-foreground text-center py-2">
                                    No episodes found
                                  </p>
                                ) : (
                                  group.episodes.map((episode) => {
                                    const episodeEnabled =
                                      enabledEpisodeIds.has(episode.id)
                                    return (
                                      <div
                                        key={episode.id}
                                        className="flex items-center gap-2 p-2 hover:bg-accent/30 rounded"
                                      >
                                        <span className="flex-1 text-sm ml-8">
                                          {getEpisodeLabel(episode)}
                                          {episodeEnabled &&
                                            episodeExpiry.get(episode.id) && (
                                              <span className="ml-2 text-xs text-muted-foreground">
                                                (until{" "}
                                                {new Date(
                                                  episodeExpiry.get(
                                                    episode.id,
                                                  )!,
                                                ).toLocaleString()}
                                                )
                                              </span>
                                            )}
                                        </span>
                                        <SourceFavicons
                                          showIds={episode.show_ids}
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
                </div>
              </DialogBody>

              <DialogFooter>
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
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>

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
          initialExpiry={episodeExpiry.get(pendingEpisode.id) ?? ""}
          onConfirm={confirmEpisodeExpiry}
          onOpenChange={(open) => {
            if (!open) setPendingEpisode(null)
          }}
        />
      )}
    </>
  )
}
