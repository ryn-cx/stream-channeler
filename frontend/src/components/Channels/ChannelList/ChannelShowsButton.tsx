// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { List } from "lucide-react"
import { useState } from "react"
import { ChannelsService } from "@/client"
import { ShowCards } from "@/components/Channels/ShowCards"
import {
  type TriggerVariant,
  VariantTrigger,
} from "@/components/Common/VariantTrigger"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

interface ChannelShowsButtonProps {
  channelId: string
  variant?: TriggerVariant
}

export function ChannelShowsButton({
  channelId,
  variant = "icon",
}: ChannelShowsButtonProps) {
  const [isOpen, setIsOpen] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ["channelShows", channelId],
    queryFn: () => ChannelsService.getChannelShows({ channelId }),
    enabled: isOpen,
  })

  const groups = (data?.groups ?? [])
    .map((group) => ({
      ...group,
      shows: (group.shows ?? []).filter((show) => !!show.name),
    }))
    .filter((group) => group.shows.length > 0)
  const hasShows = groups.some((group) => group.shows.length > 0)

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <VariantTrigger
          variant={variant}
          icon={List}
          label="Shows"
          iconTitle="List shows"
        />
      </DialogTrigger>
      <DialogContent className="sm:max-w-[calc(100%-2rem)] max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Shows</DialogTitle>
          <DialogDescription>
            All shows included in this channel.
          </DialogDescription>
        </DialogHeader>
        <div className="overflow-y-auto flex-1 min-h-0">
          {isLoading ? (
            <p className="text-sm text-muted-foreground py-4">Loading...</p>
          ) : !hasShows ? (
            <p className="text-sm text-muted-foreground py-4">
              No shows in this channel yet.
            </p>
          ) : (
            <div className="space-y-4 py-2">
              {groups.map((group) => (
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
                    stats={data?.stats ?? {}}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
