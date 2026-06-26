// TODO: Validate
import { useQueries } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"

import { ChannelsService } from "@/client"
import { ModalContent } from "@/components/Common/ModalContent"
import {
  Dialog,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import type { EpisodeWithDetails } from "./columns"

interface ChannelListDialogProps {
  episode: EpisodeWithDetails
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ChannelListDialog({
  episode,
  open,
  onOpenChange,
}: ChannelListDialogProps) {
  // Every in-scope channel (within the channel being viewed) that includes this episode.
  const channelIds =
    episode.channel_ids && episode.channel_ids.length > 0
      ? episode.channel_ids
      : [episode.channel_id]

  const channelQueries = useQueries({
    queries: channelIds.map((channelId) => ({
      queryKey: ["channel", channelId],
      queryFn: () => ChannelsService.getChannel({ channelId }),
      enabled: open,
      staleTime: 5 * 60 * 1000,
    })),
  })

  const isLoading = channelQueries.some((query) => query.isLoading)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <ModalContent>
        <DialogHeader>
          <DialogTitle>Channels</DialogTitle>
          <DialogDescription>
            Channels that include "{episode.name ?? ""}".
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-1 py-2">
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading channels…</p>
          ) : (
            channelIds.map((channelId, index) => {
              const channel = channelQueries[index].data
              const number =
                channel?.channel_number != null
                  ? `${channel.channel_number}. `
                  : ""
              const name = channel?.name ?? "Channel"
              return (
                <Link
                  key={channelId}
                  to="/channels/$channelId"
                  params={{ channelId }}
                  onClick={() => onOpenChange(false)}
                  className="rounded-md px-3 py-2 text-sm text-primary hover:bg-accent hover:underline"
                >
                  {number}
                  {name}
                </Link>
              )
            })
          )}
        </div>
      </ModalContent>
    </Dialog>
  )
}
