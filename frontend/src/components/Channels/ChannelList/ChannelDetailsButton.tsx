// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { Info } from "lucide-react"
import { useState } from "react"
import { ChannelsService } from "@/client"
import { ChannelDescriptionMarkdown } from "@/components/Channels/ChannelDetail/ChannelDescription"
import { ShowCards } from "@/components/Channels/ShowCards"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

interface ChannelDetailsButtonProps {
  channel: { id: string; name?: string | null; description?: string | null }
  showLabel?: boolean
}

// TODO: Validate
export function ChannelDetailsButton({
  channel,
  showLabel,
}: ChannelDetailsButtonProps) {
  const [isOpen, setIsOpen] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ["channelShows", channel.id],
    queryFn: () => ChannelsService.getChannelShows({ channelId: channel.id }),
    enabled: isOpen,
  })

  const canonicalShows = data?.canonical_shows ?? {}
  const groups = (data?.groups ?? [])
    .map((group) => ({
      ...group,
      shows: (group.shows ?? []).filter((show) =>
        show.canonical_show_id
          ? !!canonicalShows[show.canonical_show_id]?.name
          : !!show.name,
      ),
    }))
    .filter((group) => group.shows.length > 0)

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <TooltipIconButton
          label="Details"
          icon={<Info className="size-4" />}
          showLabel={showLabel}
        />
      </DialogTrigger>
      <DialogContent className="max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>{channel.name ?? "Channel"}</DialogTitle>
          <DialogDescription>
            The channel's description and every show it includes.
          </DialogDescription>
        </DialogHeader>
        <DialogBody className="space-y-4 py-2">
          {channel.description && (
            <ChannelDescriptionMarkdown description={channel.description} />
          )}

          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading shows...</p>
          ) : groups.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No shows in this channel yet.
            </p>
          ) : (
            groups.map((group) => (
              <div key={group.channel_id} className="space-y-1">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  <Link
                    to="/channels/$channelId"
                    params={{ channelId: group.channel_id }}
                    className="hover:text-foreground hover:underline"
                  >
                    {group.channel_name || "Unnamed Channel"}
                  </Link>
                </h3>
                <ShowCards
                  shows={group.shows}
                  sources={data?.sources ?? {}}
                  canonicalShows={data?.canonical_shows ?? {}}
                  canonicalSources={data?.canonical_sources ?? {}}
                  stats={data?.stats ?? {}}
                />
              </div>
            ))
          )}
        </DialogBody>
      </DialogContent>
    </Dialog>
  )
}
