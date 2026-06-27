// TODO: Validate
import { useQueries } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { MapPin, Radio } from "lucide-react"
import { useState } from "react"

import { type ChannelOutput, ChannelsService } from "@/client"
import { ModalContent } from "@/components/Common/ModalContent"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
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
import { cn } from "@/lib/utils"
import type { EpisodeWithDetails } from "./columns"
import { isoToLocalInput, localInputToIso } from "./expiry"

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
  owned: boolean
}

export function BlacklistEpisodeDialog({
  episode,
  currentChannelId,
  open,
  onOpenChange,
}: BlacklistEpisodeDialogProps) {
  const [expiresAtLocal, setExpiresAtLocal] = useState(() =>
    isoToLocalInput(new Date().toISOString()),
  )
  // The current channel is pre-selected since blacklisting from a card usually means
  // "hide it here". Only channels the user owns can actually be selected.
  const [selectedChannelIds, setSelectedChannelIds] = useState<Set<string>>(
    () => new Set([currentChannelId]),
  )
  const { user } = useAuth()
  const mutation = useBlacklistEpisode(currentChannelId)

  // The episode can belong to several base channels; the user may also blacklist it on
  // the channel they're currently viewing.
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
      (target): target is Omit<BlacklistTarget, "owned"> =>
        target.channel != null,
    )
    .map((target) => ({
      ...target,
      owned: target.channel.user_id === user?.id,
    }))

  // Only channels the user owns can be edited; the rest are shown for context.
  const selectedOwned = targets.filter(
    (target) => target.owned && selectedChannelIds.has(target.id),
  )

  const toggleChannel = (channelId: string) => {
    setSelectedChannelIds((previous) => {
      const next = new Set(previous)
      if (next.has(channelId)) {
        next.delete(channelId)
      } else {
        next.add(channelId)
      }
      return next
    })
  }

  const handleBlacklist = (permanent: boolean) => {
    if (selectedOwned.length === 0) return
    const expiresAt = permanent ? null : localInputToIso(expiresAtLocal)
    for (const target of selectedOwned) {
      mutation.mutate({
        targetChannelId: target.id,
        showId: episode.show.id,
        episodeId: episode.id,
        expiresAt,
      })
    }
    onOpenChange(false)
  }

  const targetLabel = (target: BlacklistTarget) => {
    const number =
      target.channel.channel_number != null
        ? `${target.channel.channel_number}. `
        : ""
    const name = target.channel.name ?? "Channel"
    return `${number}${name}`
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <ModalContent>
        <DialogHeader>
          <DialogTitle>Blacklist Episode</DialogTitle>
          <DialogDescription>
            Choose which channels to hide "{episode.name ?? ""}" from. Channels
            owned by other users are shown for reference but can't be edited.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3 py-2">
          <div className="flex flex-col gap-1">
            {isLoading ? (
              <p className="text-sm text-muted-foreground">Loading channels…</p>
            ) : targets.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                This episode isn't on any channels you can see.
              </p>
            ) : (
              targets.map((target) => (
                <div key={target.id} className="flex items-center gap-2">
                  {target.owned ? (
                    <Checkbox
                      id={`blacklist-${target.id}`}
                      checked={selectedChannelIds.has(target.id)}
                      onCheckedChange={() => toggleChannel(target.id)}
                    />
                  ) : (
                    <span className="size-4 shrink-0" aria-hidden />
                  )}
                  <label
                    htmlFor={
                      target.owned ? `blacklist-${target.id}` : undefined
                    }
                    className={cn(
                      "flex-1 text-sm",
                      !target.owned && "text-muted-foreground",
                    )}
                  >
                    {targetLabel(target)}
                    {!target.owned && " — can't edit"}
                  </label>
                  {target.isCurrent ? (
                    <span className="inline-flex items-center gap-1.5 px-3 text-sm text-muted-foreground">
                      <MapPin className="size-4" />
                      Current channel
                    </span>
                  ) : (
                    <Button asChild variant="outline" size="sm">
                      <Link
                        to="/channels/$channelId"
                        params={{ channelId: target.id }}
                        onClick={() => onOpenChange(false)}
                      >
                        <Radio className="size-4" />
                        Go to channel
                      </Link>
                    </Button>
                  )}
                </div>
              ))
            )}
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="blacklist-expiry">Blacklist until</Label>
            <Input
              id="blacklist-expiry"
              type="datetime-local"
              value={expiresAtLocal}
              onChange={(event) => setExpiresAtLocal(event.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Used by "Blacklist Temporarily". Use "Blacklist Permanently" to
              blacklist with no expiry.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={() => handleBlacklist(false)}
            disabled={selectedOwned.length === 0}
          >
            Blacklist Temporarily
            {selectedOwned.length > 1 ? ` (${selectedOwned.length})` : ""}
          </Button>
          <Button
            variant="destructive"
            onClick={() => handleBlacklist(true)}
            disabled={selectedOwned.length === 0}
          >
            Blacklist Permanently
            {selectedOwned.length > 1 ? ` (${selectedOwned.length})` : ""}
          </Button>
        </DialogFooter>
      </ModalContent>
    </Dialog>
  )
}
