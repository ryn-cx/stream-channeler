// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ChevronDown, ChevronRight } from "lucide-react"
import { useEffect, useState } from "react"
import type {
  WhitelistEpisodeOutput,
  WhitelistSeasonOutput,
  WhitelistTitleInput,
} from "@/client"
import { ChannelsService } from "@/client"
import { TitleInformationSummary } from "@/components/ChannelCommon/TitleInformationDialog"
import { Button } from "@/components/ui/button"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { ChannelEpisodeOrderField } from "./ChannelEpisodeOrderField"
import { EpisodeExpiryDialog } from "./EpisodeExpiryDialog"
import { isExpired, isoToLocalInput, localInputToIso } from "./expiry"
import { ExternalMediaLink, MediaPageButton } from "./MediaPageButton"
import { episodeLabel, SeasonEpisodes } from "./SeasonEpisodes"
import { SourceFavicons } from "./SourceFavicons"
import { groupBySource, SourceGroupRow } from "./SourceGroupRow"

/**
 * A change the user has made to one episode's entry, before it is saved.
 *
 * The episodes are read a season at a time, so the entries cannot be held as
 * the whole set of marked episodes the way the sources and seasons are. What is
 * held is what the user has altered, which is read against whatever the server
 * said about each episode as its season arrives, and is all that has to be sent
 * back: the server takes each entry on its own and leaves the rest alone.
 */
interface EpisodeChange {
  // The website's own row for the episode, which is what an entry is sent as.
  episodeId: string
  marked: boolean
  // A datetime-local input value, or "" for an entry that never expires.
  expiry: string
}

interface WhitelistManagerProps {
  channelId: string
  tmdbTitleId: string
  onClose: () => void
  /**
   * Whether the filters are only being read, which is what somebody who does not
   * own the channel gets. The title, its sites, its seasons and their episodes
   * are all still listed; what the channel has of them is the owner's to
   * set, so nothing that would set it is shown.
   */
  readOnly?: boolean
}

// TODO: Validate
function seasonLabel(season: WhitelistSeasonOutput) {
  if (season.name) {
    return season.name
  }
  return `Season ${season.season_number ?? "?"}`
}

// TODO: Validate
export function WhitelistManager({
  channelId,
  tmdbTitleId,
  onClose,
  readOnly = false,
}: WhitelistManagerProps) {
  const [isWhitelist, setIsWhitelist] = useState(false)
  // The `Title` ids of the websites' links that have a filter entry.
  const [enabledSourceIds, setEnabledSourceIds] = useState<Set<string>>(
    new Set(),
  )
  const [enabledSeasonIds, setEnabledSeasonIds] = useState<Set<string>>(
    new Set(),
  )
  // A filter is about the episode rather than one season's listing of it, so a
  // change is held by the identifier the entry names and moves with it.
  const [episodeChanges, setEpisodeChanges] = useState<
    Map<string, EpisodeChange>
  >(new Map())
  const [expandedSeasons, setExpandedSeasons] = useState<Set<string>>(new Set())
  const [sourcesExpanded, setSourcesExpanded] = useState(true)
  const [seasonsExpanded, setSeasonsExpanded] = useState(true)
  // Episode awaiting the expiry popup before being added to the filter, with
  // whether its own season has an entry, which the popup's wording reads.
  const [pendingEpisode, setPendingEpisode] = useState<{
    episode: WhitelistEpisodeOutput
    seasonEnabled: boolean
  } | null>(null)

  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const { data: whitelistData, isLoading } = useQuery({
    queryKey: ["channelTitleWhitelist", channelId, tmdbTitleId],
    queryFn: () =>
      ChannelsService.getChannelWhitelist({ channelId, tmdbTitleId }),
  })

  useEffect(() => {
    if (whitelistData) {
      setIsWhitelist(whitelistData.is_whitelist ?? false)
      setEnabledSourceIds(
        new Set(
          whitelistData.sources
            .filter((source) => source.filtered)
            .map((source) => source.title_id),
        ),
      )
      setEnabledSeasonIds(
        new Set(
          whitelistData.seasons
            .filter((season) => season.filtered)
            .map((season) => season.id),
        ),
      )
      setEpisodeChanges(new Map())
    }
  }, [whitelistData])

  const saveMutation = useMutation({
    mutationFn: (input: WhitelistTitleInput) =>
      ChannelsService.updateChannelWhitelist({
        channelId,
        tmdbTitleId,
        requestBody: input,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["channelTitleWhitelist", channelId, tmdbTitleId],
      })
      queryClient.invalidateQueries({
        queryKey: ["channelTitleSeasonEpisodes", channelId, tmdbTitleId],
      })
      queryClient.invalidateQueries({
        queryKey: ["channelTitleFilteredEpisodes", channelId, tmdbTitleId],
      })
      queryClient.invalidateQueries({ queryKey: ["episodes", channelId] })
      queryClient.invalidateQueries({
        queryKey: ["episodes-preview", channelId],
      })
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
  const toggleSeasonExpanded = (seasonId: string) => {
    const newExpanded = new Set(expandedSeasons)
    if (newExpanded.has(seasonId)) {
      newExpanded.delete(seasonId)
    } else {
      newExpanded.add(seasonId)
    }
    setExpandedSeasons(newExpanded)
  }

  // TODO: Validate
  const toggleSourceEnabled = (titleId: string) => {
    const newEnabled = new Set(enabledSourceIds)
    if (newEnabled.has(titleId)) {
      newEnabled.delete(titleId)
    } else {
      newEnabled.add(titleId)
    }
    setEnabledSourceIds(newEnabled)
  }

  // TODO: Validate
  const toggleSeasonEnabled = (seasonId: string, enabled: boolean) => {
    const newEnabled = new Set(enabledSeasonIds)
    if (enabled) {
      newEnabled.delete(seasonId)
    } else {
      newEnabled.add(seasonId)
    }
    setEnabledSeasonIds(newEnabled)
  }

  // An episode reads as the user left it where they have touched it, and as the
  // server has it everywhere else.
  // TODO: Validate
  const isEpisodeMarked = (episode: WhitelistEpisodeOutput) => {
    const change = episodeChanges.get(episode.tmdb_episode_id)
    if (change) return change.marked
    return episode.filtered && !isExpired(episode.expires_at)
  }

  // TODO: Validate
  const episodeExpiry = (episode: WhitelistEpisodeOutput) => {
    const change = episodeChanges.get(episode.tmdb_episode_id)
    if (change) return change.expiry
    if (!episode.expires_at || isExpired(episode.expires_at)) return ""
    return isoToLocalInput(episode.expires_at)
  }

  // TODO: Validate
  const recordEpisodeChange = (
    episode: WhitelistEpisodeOutput,
    marked: boolean,
    expiry: string,
  ) => {
    setEpisodeChanges((previous) => {
      const next = new Map(previous)
      next.set(episode.tmdb_episode_id, {
        episodeId: episode.tmdb_episode_id,
        marked,
        expiry,
      })
      return next
    })
  }

  // TODO: Validate
  const handleEpisodeClick = (episode: WhitelistEpisodeOutput) => {
    recordEpisodeChange(episode, !isEpisodeMarked(episode), "")
  }

  // TODO: Validate
  const handleEpisodeTemporaryClick = (
    episode: WhitelistEpisodeOutput,
    seasonEnabled: boolean,
  ) => {
    setPendingEpisode({ episode, seasonEnabled })
  }

  // TODO: Validate
  const confirmEpisodeExpiry = (expiresAtLocal: string) => {
    if (!pendingEpisode) return
    recordEpisodeChange(pendingEpisode.episode, true, expiresAtLocal)
    setPendingEpisode(null)
  }

  // TODO: Validate
  const handleSave = () => {
    if (!whitelistData) return

    const input: WhitelistTitleInput = {
      is_whitelist: isWhitelist,
      sources: whitelistData.sources
        .filter((source) => !source.is_tmdb)
        .map((source) => ({
          id: source.title_id,
          marked: enabledSourceIds.has(source.title_id),
        })),
      seasons: whitelistData.seasons.map((season) => ({
        id: season.id,
        marked: enabledSeasonIds.has(season.id),
      })),
      // Only what the user altered is sent. The server takes each entry on its
      // own, so the episodes whose seasons were never opened keep whatever they
      // already had rather than being read as unmarked.
      episodes: [...episodeChanges.values()].map((change) => ({
        id: change.episodeId,
        marked: change.marked,
        expires_at: change.marked ? localInputToIso(change.expiry) : null,
      })),
    }
    saveMutation.mutate(input)
  }

  // TODO: Validate
  const getSeasonActionDescription = (enabled: boolean, seasonName: string) => {
    if (isWhitelist) {
      return enabled
        ? `Stop showing ${seasonName} in the channel.`
        : `Show ${seasonName} in the channel.`
    }
    return enabled
      ? `Show ${seasonName} in the channel again.`
      : `Hide every episode in ${seasonName} from the channel.`
  }

  // TODO: Validate
  const getEpisodeActionDescription = (
    episodeEnabled: boolean,
    seasonEnabled: boolean,
    episodeName: string,
  ) => {
    if (isWhitelist) {
      if (seasonEnabled) {
        return episodeEnabled
          ? `Show ${episodeName} with the rest of its whitelisted season.`
          : `Leave ${episodeName} out of its whitelisted season.`
      }
      return episodeEnabled
        ? `Stop showing ${episodeName} in the channel.`
        : `Show ${episodeName} in the channel.`
    }
    if (seasonEnabled) {
      return episodeEnabled
        ? `Hide ${episodeName} with the rest of its blacklisted season.`
        : `Show ${episodeName} even though its season is blacklisted.`
    }
    return episodeEnabled
      ? `Show ${episodeName} in the channel again.`
      : `Hide ${episodeName} from the channel.`
  }

  // TODO: Validate
  const getEpisodeTemporaryDescription = (
    seasonEnabled: boolean,
    episodeName: string,
  ) => {
    if (seasonEnabled) {
      return `Show ${episodeName} until a date you pick, then hide it with the rest of its blacklisted season.`
    }
    return `Hide ${episodeName} from the channel until a date you pick.`
  }

  // TODO: Validate
  const getSeasonActionLabel = (enabled: boolean) => {
    if (isWhitelist) {
      return enabled ? "Unwhitelist" : "Whitelist"
    }
    return enabled ? "Unblacklist" : "Blacklist"
  }

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
        return episodeEnabled ? "Whitelist" : "Unwhitelist"
      }
      return episodeEnabled ? "Unwhitelist" : "Whitelist"
    }
    if (seasonEnabled) {
      return episodeEnabled ? "Blacklist" : "Unblacklist"
    }
    return episodeEnabled ? "Unblacklist" : "Blacklist"
  }

  if (!whitelistData) return
  const sourcesByTitleId = new Map(
    whitelistData.sources.map((source) => [source.title_id, source]),
  )
  // TMDB catalogues the media rather than offering it, so it never stands for a
  // site an episode can be watched on.
  const tmdbTitleIds = new Set(
    whitelistData.sources
      .filter((source) => source.is_tmdb)
      .map((source) => source.title_id),
  )
  // TMDB is listed with the sites rather than left out, so the title it was
  // catalogued under can be seen and opened from here. It has nothing to
  // watch, so it is shown without a mark and `handleSave` never sends one.
  const listedSources = whitelistData.sources
  // A site lists a title under one row most of the time and under several
  // where it splits the title up, so the rows are gathered under the site and
  // a site with one of them is read without a level in between.
  const sourceGroups = groupBySource(listedSources)

  return (
    <>
      <div className="flex flex-col gap-4">
        <TitleInformationSummary titleId={tmdbTitleId} />

        {!readOnly && (
          <ChannelEpisodeOrderField
            channelId={channelId}
            tmdbTitleId={tmdbTitleId}
          />
        )}

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <p className="text-sm text-muted-foreground">Loading...</p>
          </div>
        ) : (
          <>
            <div className="flex flex-col gap-4">
              <div className="flex flex-wrap items-center justify-between gap-2 p-4 border rounded-md bg-muted/50 shrink-0">
                <div className="min-w-0">
                  <h3 className="font-semibold">
                    Current Mode:{" "}
                    {isWhitelist ? "Whitelist Mode" : "Blacklist Mode"}
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    {isWhitelist
                      ? "Only whitelisted episodes will be shown. New episodes won't be added to the channel automatically."
                      : "All episodes except blacklisted ones will be shown. New episodes will be added to the channel automatically."}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  {!readOnly && (
                    <Button onClick={toggleIsWhitelist} variant="outline">
                      Switch to {isWhitelist ? "Blacklist" : "Whitelist"} Mode
                    </Button>
                  )}
                  <MediaPageButton
                    to="/seasons"
                    search={{ title_id: tmdbTitleId }}
                    label="Edit this title"
                  />
                </div>
              </div>

              <div className="border rounded-md shrink-0">
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
                    {isWhitelist && (
                      <p className="text-sm text-muted-foreground">
                        Only whitelisted sites are watched for this title.
                        Whitelisting none watches them all.
                      </p>
                    )}
                  </div>
                </div>
                {sourcesExpanded && (
                  <div className="border-t px-4 py-2">
                    {listedSources.length === 0 ? (
                      <p className="text-sm text-muted-foreground text-center py-4">
                        No sources found for this title
                      </p>
                    ) : (
                      <table className="w-full">
                        <thead>
                          <tr className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                            <th className="p-2 font-medium">Source</th>
                            <th className="p-2 font-medium">Title</th>
                            <th className="p-2" />
                          </tr>
                        </thead>
                        {sourceGroups.map((group) => (
                          <SourceGroupRow
                            key={group.sourceId}
                            group={group}
                            isWhitelist={isWhitelist}
                            enabledSourceIds={enabledSourceIds}
                            onToggleEnabled={toggleSourceEnabled}
                          />
                        ))}
                      </table>
                    )}
                  </div>
                )}
              </div>

              <div className="border rounded-md shrink-0">
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
                    {isWhitelist && (
                      <p className="text-sm text-muted-foreground">
                        Only whitelisted seasons and episodes will appear
                      </p>
                    )}
                  </div>
                </div>
                {seasonsExpanded && (
                  <div className="p-2 space-y-1 border-t">
                    {whitelistData.seasons.length === 0 ? (
                      <p className="text-sm text-muted-foreground text-center py-4">
                        No seasons found for this title
                      </p>
                    ) : (
                      whitelistData.seasons.map((season) => {
                        const seasonEnabled = enabledSeasonIds.has(season.id)
                        const rowTitleIds = season.title_ids
                        const tmdbRowTitleIds = rowTitleIds.filter((titleId) =>
                          tmdbTitleIds.has(titleId),
                        )
                        // TMDB leads the row, and the sites stand in front of the
                        // name only when TMDB has no record of the season to lead it.
                        const leadingTitleIds =
                          tmdbRowTitleIds.length > 0
                            ? tmdbRowTitleIds
                            : rowTitleIds
                        const trailingTitleIds =
                          tmdbRowTitleIds.length > 0
                            ? rowTitleIds.filter(
                                (titleId) => !tmdbTitleIds.has(titleId),
                              )
                            : []
                        return (
                          <div key={season.id}>
                            <div className="flex items-center gap-2 p-2 hover:bg-accent/30 rounded-md">
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                onClick={() => toggleSeasonExpanded(season.id)}
                              >
                                {expandedSeasons.has(season.id) ? (
                                  <ChevronDown className="h-4 w-4" />
                                ) : (
                                  <ChevronRight className="h-4 w-4" />
                                )}
                              </Button>
                              {leadingTitleIds.length > 0 && (
                                <SourceFavicons
                                  titleIds={leadingTitleIds}
                                  sourcesByTitleId={sourcesByTitleId}
                                />
                              )}
                              <button
                                type="button"
                                className="min-w-0 flex-1 truncate text-left text-sm hover:underline"
                                onClick={() => toggleSeasonExpanded(season.id)}
                              >
                                {seasonLabel(season)}
                              </button>
                              {trailingTitleIds.length > 0 && (
                                <SourceFavicons
                                  titleIds={trailingTitleIds}
                                  sourcesByTitleId={sourcesByTitleId}
                                />
                              )}
                              {!readOnly && (
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button
                                      className="shrink-0"
                                      variant={
                                        seasonEnabled ? "default" : "outline"
                                      }
                                      size="sm"
                                      onClick={() =>
                                        toggleSeasonEnabled(
                                          season.id,
                                          seasonEnabled,
                                        )
                                      }
                                    >
                                      {getSeasonActionLabel(seasonEnabled)}
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    {getSeasonActionDescription(
                                      seasonEnabled,
                                      seasonLabel(season),
                                    )}
                                  </TooltipContent>
                                </Tooltip>
                              )}
                              <ExternalMediaLink
                                url={season.url}
                                label="Open this season on its site"
                              />
                              <MediaPageButton
                                to="/episodes"
                                search={{ season_id: season.id }}
                                label="Open this season here"
                              />
                            </div>

                            {expandedSeasons.has(season.id) && (
                              <SeasonEpisodes
                                channelId={channelId}
                                tmdbTitleId={tmdbTitleId}
                                seasonId={season.id}
                                seasonEnabled={seasonEnabled}
                                sourcesByTitleId={sourcesByTitleId}
                                tmdbTitleIds={tmdbTitleIds}
                                isEpisodeMarked={isEpisodeMarked}
                                episodeExpiry={episodeExpiry}
                                onEpisodeClick={handleEpisodeClick}
                                onEpisodeTemporaryClick={
                                  isWhitelist
                                    ? undefined
                                    : (episode) =>
                                        handleEpisodeTemporaryClick(
                                          episode,
                                          seasonEnabled,
                                        )
                                }
                                episodeActionLabel={getEpisodeActionLabel}
                                episodeActionDescription={
                                  getEpisodeActionDescription
                                }
                                episodeTemporaryDescription={(episodeName) =>
                                  getEpisodeTemporaryDescription(
                                    seasonEnabled,
                                    episodeName,
                                  )
                                }
                                readOnly={readOnly}
                              />
                            )}
                          </div>
                        )
                      })
                    )}
                  </div>
                )}
              </div>
            </div>

            {!readOnly && (
              <div className="flex justify-end gap-2">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      onClick={onClose}
                      disabled={saveMutation.isPending}
                    >
                      Cancel
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    Close without keeping any of the marks made here.
                  </TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <LoadingButton
                      onClick={handleSave}
                      loading={saveMutation.isPending}
                    >
                      Save Changes
                    </LoadingButton>
                  </TooltipTrigger>
                  <TooltipContent>
                    Save every mark made here to the channel.
                  </TooltipContent>
                </Tooltip>
              </div>
            )}
          </>
        )}
      </div>

      {pendingEpisode && (
        <EpisodeExpiryDialog
          open={!!pendingEpisode}
          // The popup only opens when adding an episode-level entry, so the action
          // matches the not-yet-enabled label (which already accounts for the season).
          title={getEpisodeActionLabel(false, pendingEpisode.seasonEnabled)}
          description={episodeLabel(pendingEpisode.episode)}
          dateLabel="Expires at (optional)"
          confirmLabel={getEpisodeActionLabel(
            false,
            pendingEpisode.seasonEnabled,
          )}
          initialExpiry={episodeExpiry(pendingEpisode.episode)}
          onConfirm={confirmEpisodeExpiry}
          onOpenChange={(open) => {
            if (!open) setPendingEpisode(null)
          }}
        />
      )}
    </>
  )
}
