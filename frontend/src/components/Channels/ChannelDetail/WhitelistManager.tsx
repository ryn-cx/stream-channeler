// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ChevronDown, ChevronRight } from "lucide-react"
import { useEffect, useState } from "react"
import type { EpisodeOutput, SeasonOutput, WhitelistShowInput } from "@/client"
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
  const [whitelistMode, setWhitelistMode] = useState(false)
  const [enabledSeasonIds, setEnabledSeasonIds] = useState<Set<string>>(
    new Set(),
  )
  const [enabledEpisodeIds, setEnabledEpisodeIds] = useState<Set<string>>(
    new Set(),
  )
  const [expandedSeasons, setExpandedSeasons] = useState<Set<string>>(new Set())

  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const { data: whitelistData, isLoading } = useQuery({
    queryKey: ["channelShowWhitelist", channelId, showId],
    queryFn: () =>
      ChannelsService.getChannelShowWhitelist({ channelId, showId }),
    enabled: isOpen,
  })

  useEffect(() => {
    if (whitelistData) {
      setWhitelistMode(whitelistData.whitelist_mode ?? false)
      setEnabledSeasonIds(new Set(whitelistData.enabled_season_ids ?? []))
      setEnabledEpisodeIds(new Set(whitelistData.enabled_episode_ids ?? []))
    }
  }, [whitelistData])

  const saveMutation = useMutation({
    mutationFn: (input: WhitelistShowInput) =>
      ChannelsService.setChannelShowWhitelist({
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
    onError: (error) => {
      handleError.call(showErrorToast, error as any)
    },
  })

  const toggleWhitelistMode = () => {
    setWhitelistMode(!whitelistMode)
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

  const handleSave = () => {
    if (!whitelistData) return

    const episodesBySeason = new Map<string, typeof whitelistData.episodes>()
    whitelistData.episodes.forEach((episode) => {
      const seasonEpisodes = episodesBySeason.get(episode.season_id) || []
      seasonEpisodes.push(episode)
      episodesBySeason.set(episode.season_id, seasonEpisodes)
    })

    const input: WhitelistShowInput = {
      id: showId,
      whitelist_mode: whitelistMode,
      seasons: whitelistData.seasons.map((season) => ({
        id: season.id,
        enabled: enabledSeasonIds.has(season.id),
        episodes:
          episodesBySeason.get(season.id)?.map((episode) => ({
            id: episode.id,
            enabled: enabledEpisodeIds.has(episode.id),
          })) || [],
      })),
    }
    saveMutation.mutate(input)
  }

  const getSeasonLabel = (season: SeasonOutput) => {
    const seasonNum = season.season_number ?? "?"
    const seasonName = season.name ? ` - ${season.name}` : ""
    return `Season ${seasonNum}${seasonName}`
  }

  const getEpisodeLabel = (episode: EpisodeOutput) => {
    const episodeName = episode.name ? ` - ${episode.name}` : ""
    return `Episode ${episode.sort_order ?? "?"}${episodeName}`
  }

  const getStatusLabel = (enabled: boolean) => {
    if (whitelistMode) {
      return enabled ? "Whitelisted" : "Not Whitelisted"
    }
    return enabled ? "Blacklisted" : "Not Blacklisted"
  }

  const getStatusButtonText = (enabled: boolean) => {
    if (whitelistMode) {
      return enabled ? "Remove from Whitelist" : "Add to Whitelist"
    }
    return enabled ? "Remove from Blacklist" : "Add to Blacklist"
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
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-3xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Manage Whitelist - {showName}</DialogTitle>
          <DialogDescription>
            Configure which episodes are included or excluded from the channel
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
                    {whitelistMode ? "Whitelist Mode" : "Blacklist Mode"}
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    {whitelistMode
                      ? "Only whitelisted episodes will be shown"
                      : "All episodes except blacklisted ones will be shown"}
                  </p>
                </div>
                <Button onClick={toggleWhitelistMode} variant="outline">
                  Switch to {whitelistMode ? "Blacklist" : "Whitelist"} Mode
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
                            <span className="text-sm text-muted-foreground mr-2">
                              {getStatusLabel(seasonEnabled)}
                            </span>
                            <Button
                              variant={seasonEnabled ? "default" : "outline"}
                              size="sm"
                              onClick={() => toggleSeasonEnabled(season.id)}
                            >
                              {getStatusButtonText(seasonEnabled)}
                            </Button>
                          </div>

                          {expandedSeasons.has(season.id) && (
                            <div className="p-2 space-y-1">
                              {!episodesBySeason.get(season.id) ||
                              episodesBySeason.get(season.id)!.length === 0 ? (
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
                                        </span>
                                        <span className="text-xs text-muted-foreground mr-2">
                                          {getStatusLabel(episodeEnabled)}
                                        </span>
                                        <Button
                                          variant={
                                            episodeEnabled
                                              ? "default"
                                              : "outline"
                                          }
                                          size="sm"
                                          onClick={() =>
                                            toggleEpisodeEnabled(episode.id)
                                          }
                                        >
                                          {getStatusButtonText(episodeEnabled)}
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
  )
}
