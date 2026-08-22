// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ChevronDown, ChevronRight } from "lucide-react"
import { useEffect, useState } from "react"
import type {
  WhitelistEpisodeOutput,
  WhitelistSeasonOutput,
  WhitelistShowInput,
} from "@/client"
import { ChannelsService } from "@/client"
import {
  ShowInformationSummary,
  ShowIssueReports,
} from "@/components/ChannelCommon/ShowInformationDialog"
import EditSeason from "@/components/Seasons/Edit"
import { Button } from "@/components/ui/button"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { EpisodeExpiryDialog } from "./EpisodeExpiryDialog"
import { isExpired, isoToLocalInput, localInputToIso } from "./expiry"
import {
  AdminOnly,
  ExternalMediaLink,
  MediaPageButton,
} from "./MediaPageButton"
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
  canonicalShowId: string
  showName: string
  onClose: () => void
  /**
   * Whether the filters are only being read, which is what somebody who does not
   * own the channel gets. The title, its sites, its seasons and their episodes
   * are all still listed; what the channel carries of them is the owner's to
   * set, so nothing that would set it is shown.
   */
  readOnly?: boolean
}

// TODO: Validate
function seasonLabel(
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
export function WhitelistManager({
  channelId,
  canonicalShowId,
  showName,
  onClose,
  readOnly = false,
}: WhitelistManagerProps) {
  const [isWhitelist, setIsWhitelist] = useState(false)
  // The `Show` ids of the websites' links that carry a filter entry.
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
  // whether its own season carries an entry, which the popup's wording reads.
  const [pendingEpisode, setPendingEpisode] = useState<{
    episode: WhitelistEpisodeOutput
    seasonEnabled: boolean
  } | null>(null)
  const [informationShowId, setInformationShowId] = useState<string | null>(
    null,
  )

  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const { data: whitelistData, isLoading } = useQuery({
    queryKey: ["channelShowWhitelist", channelId, canonicalShowId],
    queryFn: () =>
      ChannelsService.getChannelWhitelist({ channelId, canonicalShowId }),
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
      setEpisodeChanges(new Map())
    }
  }, [whitelistData])

  const saveMutation = useMutation({
    mutationFn: (input: WhitelistShowInput) =>
      ChannelsService.updateChannelWhitelist({
        channelId,
        canonicalShowId,
        requestBody: input,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["channelShowWhitelist", channelId, canonicalShowId],
      })
      queryClient.invalidateQueries({
        queryKey: ["channelShowSeasonEpisodes", channelId, canonicalShowId],
      })
      queryClient.invalidateQueries({
        queryKey: ["channelShowFilteredEpisodes", channelId, canonicalShowId],
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
  const toggleShowInformation = (sourceShowId: string) => {
    setInformationShowId(
      informationShowId === sourceShowId ? null : sourceShowId,
    )
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
    const change = episodeChanges.get(episode.canonical_episode_id)
    if (change) return change.marked
    return episode.filtered && !isExpired(episode.expires_at)
  }

  // TODO: Validate
  const episodeExpiry = (episode: WhitelistEpisodeOutput) => {
    const change = episodeChanges.get(episode.canonical_episode_id)
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
      next.set(episode.canonical_episode_id, {
        episodeId: episode.canonical_episode_id,
        marked,
        expiry,
      })
      return next
    })
  }

  // Clicking an episode toggles it; removing is immediate, adding first asks for the
  // optional expiry via a popup.
  // TODO: Validate
  const handleEpisodeClick = (
    episode: WhitelistEpisodeOutput,
    seasonEnabled: boolean,
  ) => {
    if (isEpisodeMarked(episode)) {
      recordEpisodeChange(episode, false, "")
    } else {
      setPendingEpisode({ episode, seasonEnabled })
    }
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
  const getSeasonActionLabel = (enabled: boolean) => {
    if (isWhitelist) {
      return enabled ? "Remove from Whitelist" : "Add to Whitelist"
    }
    return enabled ? "Remove from Blacklist" : "Add to Blacklist"
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
  // TMDB is listed with the sites rather than left out, so the title it was
  // catalogued under can be seen and opened from here. It carries nothing to
  // watch, so it is shown without a mark and `handleSave` never sends one.
  const listedSources = whitelistData.sources
  // A site carries a title under one row most of the time and under several
  // where it splits the title up, so the rows are gathered under the site and
  // a site with one of them is read without a level in between.
  const sourceGroups = groupBySource(listedSources)
  const anySeasonHasNumber = whitelistData.seasons.some(
    (season) => season.season_number != null,
  )

  return (
    <>
      <div className="flex flex-col gap-4">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold">
              {readOnly ? showName : `Manage Whitelist - ${showName}`}
            </h2>
            <p className="text-sm text-muted-foreground">
              {isWhitelist
                ? "Only selected sites, seasons and episodes will appear. New episodes are not automatically added."
                : "All episodes are shown by default. New episodes are automatically added."}
            </p>
          </div>
        </div>

        <ShowInformationSummary showId={canonicalShowId} />

        <ShowIssueReports showId={canonicalShowId} />

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
                <div className="flex items-center gap-1">
                  {!readOnly && (
                    <Button onClick={toggleIsWhitelist} variant="outline">
                      Switch to {isWhitelist ? "Blacklist" : "Whitelist"} Mode
                    </Button>
                  )}
                  <MediaPageButton
                    to="/show/$showKey"
                    params={{ showKey: canonicalShowId }}
                    label="Edit this show"
                  />
                </div>
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
                    {listedSources.length === 0 ? (
                      <p className="text-sm text-muted-foreground text-center py-4">
                        No sources found for this show
                      </p>
                    ) : (
                      sourceGroups.map((group) => (
                        <SourceGroupRow
                          key={group.sourceId}
                          group={group}
                          isWhitelist={isWhitelist}
                          enabledSourceIds={enabledSourceIds}
                          informationShowId={informationShowId}
                          onToggleInformation={toggleShowInformation}
                          onToggleEnabled={toggleSourceEnabled}
                        />
                      ))
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
                    {whitelistData.seasons.length === 0 ? (
                      <p className="text-sm text-muted-foreground text-center py-4">
                        No seasons found for this show
                      </p>
                    ) : (
                      whitelistData.seasons.map((season) => {
                        const seasonEnabled = enabledSeasonIds.has(season.id)
                        const rowShowIds = season.show_ids
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
                          <div key={season.id}>
                            <div className="flex items-center gap-2 p-2 hover:bg-accent/30 rounded">
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
                              {leadingShowIds.length > 0 && (
                                <SourceFavicons
                                  showIds={leadingShowIds}
                                  sourcesByShowId={sourcesByShowId}
                                />
                              )}
                              <button
                                type="button"
                                className="flex-1 text-left text-sm hover:underline"
                                onClick={() => toggleSeasonExpanded(season.id)}
                              >
                                {seasonLabel(season, anySeasonHasNumber)}
                              </button>
                              {trailingShowIds.length > 0 && (
                                <SourceFavicons
                                  showIds={trailingShowIds}
                                  sourcesByShowId={sourcesByShowId}
                                />
                              )}
                              {!readOnly && (
                                <Button
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
                              )}
                              <ExternalMediaLink
                                url={season.url}
                                label="Open this season on its site"
                              />
                              <AdminOnly>
                                <EditSeason season={season} />
                              </AdminOnly>
                              <MediaPageButton
                                to="/season/$seasonKey"
                                params={{ seasonKey: season.id }}
                                label="Open this season here"
                              />
                            </div>

                            {expandedSeasons.has(season.id) && (
                              <SeasonEpisodes
                                channelId={channelId}
                                canonicalShowId={canonicalShowId}
                                seasonId={season.id}
                                seasonEnabled={seasonEnabled}
                                sourcesByShowId={sourcesByShowId}
                                tmdbShowIds={tmdbShowIds}
                                isEpisodeMarked={isEpisodeMarked}
                                episodeExpiry={episodeExpiry}
                                onEpisodeClick={(episode) =>
                                  handleEpisodeClick(episode, seasonEnabled)
                                }
                                episodeActionLabel={getEpisodeActionLabel}
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
