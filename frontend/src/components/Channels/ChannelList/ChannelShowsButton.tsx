// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { List } from "lucide-react"
import { useState } from "react"
import { ChannelsService } from "@/client"
import { Button } from "@/components/ui/button"
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
}

export function ChannelShowsButton({ channelId }: ChannelShowsButtonProps) {
  const [isOpen, setIsOpen] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ["channelShows", channelId],
    queryFn: () => ChannelsService.getChannelShows({ channelId }),
    enabled: isOpen,
  })

  const shows = (data?.shows ?? [])
    .filter((show) => !!show.name)
    .sort((first, second) =>
      (first.name ?? "").localeCompare(second.name ?? ""),
    )

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" title="List shows">
          <List className="size-4" />
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Shows</DialogTitle>
          <DialogDescription>
            All shows included in this channel.
          </DialogDescription>
        </DialogHeader>
        <div className="overflow-y-auto flex-1 min-h-0">
          {isLoading ? (
            <p className="text-sm text-muted-foreground py-4">Loading...</p>
          ) : shows.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4">
              No shows in this channel yet.
            </p>
          ) : (
            <ul className="space-y-1 py-2">
              {shows.map((show) => {
                const source = data?.sources?.[show.source_id]
                return (
                  <li key={show.id} className="flex items-center gap-2 text-sm">
                    {source?.favicon_url && (
                      <img
                        src={source.favicon_url}
                        alt={`${source.name} favicon`}
                        className="size-4 shrink-0"
                      />
                    )}
                    <span>{show.name}</span>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
