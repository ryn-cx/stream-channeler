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
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { EpisodeExpiryDialog } from "./EpisodeExpiryDialog"
import { isoToLocalInput, localInputToIso } from "./expiry"

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
            .filter((episode) => episode.filtered)
            .map((episode) => episode.id),
        ),
      )
      setEpisodeExpiry(
        new Map(
          whitelistData.episodes
            .filter((episode) => episode.expires_at)
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

  const toggleSeasonExpanded = (seasonId: string) => {
    const newExpanded = new Set(expandedSeasons)
    if (newExpanded.has(seasonId)) {
      newExpanded.delete(seasonId)
    } else {
      newExpanded.add(seasonId)
    }
    setExpandedSeasons(newExpanded)
  }

  const toggleSeasonEnabled = (seasonId: string) => {
    const newEnabled = new Set(enabledSeasonIds)
    if (newEnabled.has(seasonId)) {
      newEnabled.delete(seasonId)
    } else {
      newEnabled.add(seasonId)
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

  const getSeasonLabel = (season: WhitelistSeasonOutput) => {
    const seasonNum = season.season_number ?? "?"
    const seasonName = season.name ? ` - ${season.name}` : ""
    return `Season ${seasonNum}${seasonName}`
  }

  const getEpisodeLabel = (episode: WhitelistEpisodeOutput) => {
    const episodeName = episode.name ? ` - ${episode.name}` : ""
    return `Episode ${episode.sort_order ?? "?"}${episodeName}`
  }

  const getSeasonActionLabel = (enabled: boolean) => {
    if (isWhitelist) {
      return enabled ? "Remove from Whitelist" : "Add to Whitelist"
    }
    return enabled ? "Remove from Blacklist" : "Add to Blacklist"
  }

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

  // Group episodes by season for rendering
  if (!whitelistData) return
  const episodesBySeason = new Map<string, typeof whitelistData.episodes>()
  if (whitelistData) {
    whitelistData.episodes.forEach((episode) => {
      const seasonEpisodes = episodesBySeason.get(episode.season_id) || []
      seasonEpisodes.push(episode)
      episodesBySeason.set(episode.season_id, seasonEpisodes)
    })
  }

  return (
    <>
      <Dialog open={isOpen} onOpenChange={onClose}>
        <DialogContent className="sm:max-w-3xl max-h-[80vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>Manage Whitelist - {showName}</DialogTitle>
            <DialogDescription>
              {isWhitelist
                ? "Only selected seasons and episodes will appear. New episodes are not automatically added."
                : "All episodes are shown by default. New episodes are automatically added."}
            </DialogDescription>
          </DialogHeader>

          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <p className="text-sm text-muted-foreground">Loading...</p>
            </div>
          ) : (
            <>
              <div className="flex flex-col gap-4 py-4 flex-1 min-h-0">
                <div className="flex items-center justify-between p-4 border rounded bg-muted/50 shrink-0">
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

                <div className="flex-1 overflow-y-auto border rounded min-h-0">
                  <div className="p-4 space-y-2">
                    {!whitelistData?.seasons ||
                    whitelistData.seasons.length === 0 ? (
                      <p className="text-sm text-muted-foreground text-center py-4">
                        No seasons found for this show
                      </p>
                    ) : (
                      whitelistData.seasons.map((season) => {
                        const seasonEnabled = enabledSeasonIds.has(season.id)
                        return (
                          <div key={season.id} className="border rounded">
                            <div className="flex items-center gap-2 p-3 bg-accent/50">
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
                              <span className="flex-1 font-medium">
                                {getSeasonLabel(season)}
                              </span>
                              <Button
                                variant={seasonEnabled ? "default" : "outline"}
                                size="sm"
                                onClick={() => toggleSeasonEnabled(season.id)}
                              >
                                {getSeasonActionLabel(seasonEnabled)}
                              </Button>
                            </div>

                            {expandedSeasons.has(season.id) && (
                              <div className="p-2 space-y-1">
                                {!episodesBySeason.get(season.id) ||
                                episodesBySeason.get(season.id)!.length ===
                                  0 ? (
                                  <p className="text-sm text-muted-foreground text-center py-2">
                                    No episodes found
                                  </p>
                                ) : (
                                  episodesBySeason
                                    .get(season.id)!
                                    .map((episode) => {
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
              </div>

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
            enabledSeasonIds.has(pendingEpisode.season_id),
          )}
          description={getEpisodeLabel(pendingEpisode)}
          dateLabel="Expires at (optional)"
          confirmLabel={getEpisodeActionLabel(
            false,
            enabledSeasonIds.has(pendingEpisode.season_id),
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
