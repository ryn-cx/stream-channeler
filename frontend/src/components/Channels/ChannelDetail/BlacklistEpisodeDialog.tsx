// TODO: Validate
import { useQueries } from "@tanstack/react-query"
import { useState } from "react"

import { type ChannelOutput, ChannelsService } from "@/client"
import { ModalContent } from "@/components/Common/ModalContent"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import useAuth from "@/hooks/useAuth"
import { useBlacklistEpisode } from "@/hooks/useBlacklistEpisode"
import type { EpisodeWithDetails } from "./columns"
import { localInputToIso } from "./expiry"

interface BlacklistEpisodeDialogProps {
  episode: EpisodeWithDetails
  currentChannelId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

interface BlacklistTarget {
  id: string
  channel: ChannelOutput
  isCurrent: boolean
}

export function BlacklistEpisodeDialog({
  episode,
  currentChannelId,
  open,
  onOpenChange,
}: BlacklistEpisodeDialogProps) {
  const [expiresAtLocal, setExpiresAtLocal] = useState("")
  const { user } = useAuth()
  const mutation = useBlacklistEpisode(currentChannelId)

  // The episode can belong to several base channels; the user may also blacklist it on
  // the channel they're currently viewing. Only channels the user owns are valid
  // targets (the blacklist endpoint requires ownership).
  const baseChannelIds =
    episode.channel_ids && episode.channel_ids.length > 0
      ? episode.channel_ids
      : [episode.channel_id]
  const candidateIds = Array.from(
    new Set([...baseChannelIds, currentChannelId]),
  )

  const channelQueries = useQueries({
    queries: candidateIds.map((channelId) => ({
      queryKey: ["channel", channelId],
      queryFn: () => ChannelsService.getChannel({ channelId }),
      enabled: open,
      staleTime: 5 * 60 * 1000,
    })),
  })

  const isLoading = channelQueries.some((query) => query.isLoading)

  const targets: BlacklistTarget[] = candidateIds
    .map((channelId, index) => ({
      id: channelId,
      channel: channelQueries[index].data,
      isCurrent: channelId === currentChannelId,
    }))
    .filter(
      (target): target is BlacklistTarget =>
        target.channel != null && target.channel.user_id === user?.id,
    )

  const handleBlacklist = (targetChannelId: string) => {
    const expiresAt = localInputToIso(expiresAtLocal)
    mutation.mutate({
      targetChannelId,
      showId: episode.show.id,
      episodeId: episode.id,
      expiresAt,
    })
    onOpenChange(false)
  }

  const targetLabel = (target: BlacklistTarget) => {
    const number =
      target.channel.channel_number != null
        ? `${target.channel.channel_number}. `
        : ""
    const name = target.channel.name ?? "Channel"
    const suffix = target.isCurrent ? " (current channel)" : ""
    return `${number}${name}${suffix}`
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <ModalContent>
        <DialogHeader>
          <DialogTitle>Blacklist Episode</DialogTitle>
          <DialogDescription>
            Hide "{episode.name ?? ""}" from a channel. Optionally choose when
            the blacklist should end.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-2 py-2">
          <Label htmlFor="blacklist-expiry">Blacklist until (optional)</Label>
          <Input
            id="blacklist-expiry"
            type="datetime-local"
            value={expiresAtLocal}
            onChange={(event) => setExpiresAtLocal(event.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            Leave empty to blacklist permanently.
          </p>
        </div>

        <DialogFooter className="flex-col gap-2 sm:flex-col sm:items-stretch sm:space-x-0">
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading channels…</p>
          ) : targets.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              You don't own a channel this episode can be blacklisted on.
            </p>
          ) : (
            targets.map((target) => (
              <Button
                key={target.id}
                variant="destructive"
                onClick={() => handleBlacklist(target.id)}
              >
                Blacklist on {targetLabel(target)}
              </Button>
            ))
          )}
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
        </DialogFooter>
      </ModalContent>
    </Dialog>
  )
}
