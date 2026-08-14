// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ChannelsService } from "@/client"
import { ModalContent } from "@/components/Common/ModalContent"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogBody,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface BlacklistedEpisodesDialogProps {
  channelId: string
  canonicalShowId: string
  showName: string
  isOpen: boolean
  onClose: () => void
}

// Focused view of the episodes a (usually non-member) show has blacklisted on a channel,
// letting the user remove individual blacklist entries. Reuses the whitelist endpoints:
// every episode comes back with a `filtered` flag, so the blacklisted ones are the
// filtered episodes of a blacklist-mode show.
// TODO: Validate
export function BlacklistedEpisodesDialog({
  channelId,
  canonicalShowId,
  showName,
  isOpen,
  onClose,
}: BlacklistedEpisodesDialogProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const { data: whitelistData, isLoading } = useQuery({
    queryKey: ["channelShowWhitelist", channelId, canonicalShowId],
    queryFn: () =>
      ChannelsService.getChannelWhitelist({ channelId, canonicalShowId }),
    enabled: isOpen,
  })

  const removeMutation = useMutation({
    mutationFn: (episodeId: string) =>
      ChannelsService.updateChannelWhitelist({
        channelId,
        canonicalShowId,
        requestBody: { episodes: [{ id: episodeId, marked: false }] },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["channelShowWhitelist", channelId, canonicalShowId],
      })
      queryClient.invalidateQueries({ queryKey: ["episodes", channelId] })
      // The show drops off the filter-only list once its last entry is removed.
      queryClient.invalidateQueries({ queryKey: ["channel-shows", channelId] })
      showSuccessToast("Episode removed from blacklist")
    },
    onError: handleError.bind(showErrorToast),
  })

  const seasonsById = new Map(
    (whitelistData?.seasons ?? []).map((season) => [season.id, season]),
  )
  const blacklistedEpisodes = (whitelistData?.episodes ?? []).filter(
    (episode) => episode.filtered,
  )

  // TODO: Validate
  const handleRemove = (episodeId: string) => {
    // Removing the final entry deletes the filter-only show on the backend, so
    // close the dialog instead of leaving it on a stale/missing show.
    const isLast = blacklistedEpisodes.length === 1
    removeMutation.mutate(episodeId, {
      onSuccess: () => {
        if (isLast) onClose()
      },
    })
  }

  // TODO: Validate
  const episodeLabel = (
    episode: NonNullable<typeof whitelistData>["episodes"][number],
  ) => {
    const season = seasonsById.get(episode.season_id)
    const seasonPart =
      season?.season_number != null ? `S${season.season_number} ` : ""
    const episodePart =
      episode.episode_number != null ? `E${episode.episode_number} ` : ""
    const namePart = episode.name ?? ""
    return `${seasonPart}${episodePart}${namePart}`.trim() || "Untitled episode"
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <ModalContent size="2xl">
        <DialogHeader>
          <DialogTitle>Blacklisted Episodes - {showName}</DialogTitle>
          <DialogDescription>
            Episodes hidden from this channel. Remove an entry to show the
            episode again.
          </DialogDescription>
        </DialogHeader>

        <DialogBody>
          {isLoading ? (
            <p className="text-sm text-muted-foreground py-4">Loading…</p>
          ) : blacklistedEpisodes.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4">
              This show has no blacklisted episodes.
            </p>
          ) : (
            <div className="flex flex-col gap-1 py-2">
              {blacklistedEpisodes.map((episode) => (
                <div
                  key={episode.id}
                  className="flex items-center gap-2 rounded-md border p-2"
                >
                  <div className="flex flex-1 flex-col">
                    <span className="text-sm">{episodeLabel(episode)}</span>
                    {episode.expires_at && (
                      <span className="text-xs text-muted-foreground">
                        Expires {new Date(episode.expires_at).toLocaleString()}
                      </span>
                    )}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleRemove(episode.id)}
                    disabled={removeMutation.isPending}
                  >
                    Remove
                  </Button>
                </div>
              ))}
            </div>
          )}
        </DialogBody>
      </ModalContent>
    </Dialog>
  )
}
