// TODO: Validate
import { useQueries } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { ChevronLeft, ChevronRight, Pencil, Trash2 } from "lucide-react"
import { useCallback, useEffect, useRef, useState } from "react"
import { createPortal } from "react-dom"

import { getChannelEpisodes } from "@/api/channels"
import type { ChannelOutput } from "@/client"
import type { EpisodeWithDetails } from "@/components/Channels/ChannelDetail/columns"
import { EpisodeCard } from "@/components/Channels/ChannelDetail/EpisodeCards"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import DeleteChannel from "./DeleteChannel"
import EditChannel from "./EditChannel"

interface ChannelRowProps {
  channel: ChannelOutput
  onEmpty?: (channelId: string) => void
  onEdit: (channel: ChannelOutput) => void
  onDelete: (channel: ChannelOutput) => void
}

function ChannelRow({ channel, onEmpty, onEdit, onDelete }: ChannelRowProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [showLeftArrow, setShowLeftArrow] = useState(false)
  const [showRightArrow, setShowRightArrow] = useState(true)

  const defaultOrder = channel.default_order
    ? (() => {
        try {
          return JSON.parse(channel.default_order)
        } catch {
          return {}
        }
      })()
    : {}

  const { data, isLoading } = useQueries({
    queries: [
      {
        queryKey: ["episodes-preview", channel.id, defaultOrder],
        queryFn: () =>
          getChannelEpisodes({
            channelId: channel.id,
            limit: 20,
            ...defaultOrder,
          }),
        refetchOnWindowFocus: false,
        refetchOnMount: false,
      },
    ],
  })[0]

  const updateArrows = () => {
    const container = scrollRef.current
    if (!container) return
    setShowLeftArrow(container.scrollLeft > 10)
    setShowRightArrow(
      container.scrollLeft < container.scrollWidth - container.clientWidth - 10,
    )
  }

  const scroll = (direction: "left" | "right") => {
    const container = scrollRef.current
    if (!container) return
    const scrollAmount = container.clientWidth * 0.8
    container.scrollBy({
      left: direction === "left" ? -scrollAmount : scrollAmount,
      behavior: "smooth",
    })
  }

  const episodesWithDetails: EpisodeWithDetails[] = (data?.episodes ?? []).map(
    (episode) => {
      const season = data!.seasons[episode.season_id]
      const show = data!.shows[season.show_id]
      const source = data!.sources[show.source_id]
      const plugin = data!.plugins[source.plugin_id]
      return { ...episode, season, show, source, plugin }
    },
  )

  useEffect(() => {
    if (!isLoading && episodesWithDetails.length === 0) {
      onEmpty?.(channel.id)
    }
  }, [isLoading, episodesWithDetails.length, channel.id, onEmpty])

  return (
    <div className="group/row relative">
      <div className="flex items-center gap-3 mb-2 px-[4%]">
        {channel.channel_number != null && (
          <span className="text-2xl font-bold text-muted-foreground tabular-nums">
            {channel.channel_number}
          </span>
        )}
        <Link
          to="/channels/$channelId"
          params={{ channelId: channel.id }}
          search={defaultOrder}
          className="text-2xl font-bold hover:text-primary transition-colors"
        >
          {channel.name}
        </Link>
        <div className="flex">
          <Button
            variant="ghost"
            size="icon"
            title="Edit channel"
            onClick={() => onEdit(channel)}
          >
            <Pencil className="size-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            title="Delete channel"
            onClick={() => onDelete(channel)}
          >
            <Trash2 className="size-4 text-destructive" />
          </Button>
        </div>
      </div>

      <div className="relative">
        {showLeftArrow && (
          <Button
            variant="ghost"
            size="icon"
            className="absolute left-0 top-0 bottom-0 z-20 h-full w-10 rounded-none bg-background/50 opacity-0 group-hover/row:opacity-100 transition-opacity"
            onClick={() => scroll("left")}
          >
            <ChevronLeft className="size-6" />
          </Button>
        )}

        <div
          ref={scrollRef}
          className="flex gap-2 overflow-x-auto scrollbar-hide px-[4%] pb-2"
          onScroll={updateArrows}
        >
          {isLoading
            ? Array.from({ length: 8 }).map((_, index) => (
                <Skeleton
                  key={`skeleton-${channel.id}-${index}`}
                  className="flex-shrink-0 w-[280px] md:w-[340px] lg:w-[400px] aspect-video rounded-sm"
                />
              ))
            : episodesWithDetails.map((episode) => (
                <div
                  key={episode.id}
                  className="flex-shrink-0 w-[280px] md:w-[340px] lg:w-[400px]"
                >
                  <EpisodeCard episode={episode} channelId={channel.id} />
                </div>
              ))}

          {!isLoading && episodesWithDetails.length === 0 && (
            <p className="text-sm text-muted-foreground py-8">
              No episodes in this channel yet
            </p>
          )}
        </div>

        {showRightArrow && episodesWithDetails.length > 0 && (
          <Button
            variant="ghost"
            size="icon"
            className="absolute right-0 top-0 bottom-0 z-20 h-full w-10 rounded-none bg-background/50 opacity-0 group-hover/row:opacity-100 transition-opacity"
            onClick={() => scroll("right")}
          >
            <ChevronRight className="size-6" />
          </Button>
        )}
      </div>
    </div>
  )
}

interface ChannelsBrowseProps {
  channels: ChannelOutput[]
}

export function ChannelsBrowse({ channels }: ChannelsBrowseProps) {
  const sorted = [...channels].sort((a, b) => {
    const numA = a.channel_number ?? Number.MAX_SAFE_INTEGER
    const numB = b.channel_number ?? Number.MAX_SAFE_INTEGER
    if (numA !== numB) return numA - numB
    return (a.name ?? "").localeCompare(b.name ?? "")
  })
  const [emptyChannelIds, setEmptyChannelIds] = useState<Set<string>>(new Set())
  const [editChannel, setEditChannel] = useState<ChannelOutput | null>(null)
  const [deleteChannel, setDeleteChannel] = useState<ChannelOutput | null>(null)

  const handleEmpty = useCallback((channelId: string) => {
    setEmptyChannelIds((prev) => {
      if (prev.has(channelId)) return prev
      return new Set(prev).add(channelId)
    })
  }, [])

  const withEpisodes = sorted.filter(
    (channel) => !emptyChannelIds.has(channel.id),
  )
  const withoutEpisodes = sorted.filter((channel) =>
    emptyChannelIds.has(channel.id),
  )

  return (
    <div className="flex flex-col gap-8 pb-8">
      {withEpisodes.map((channel) => (
        <ChannelRow
          key={channel.id}
          channel={channel}
          onEmpty={handleEmpty}
          onEdit={setEditChannel}
          onDelete={setDeleteChannel}
        />
      ))}
      {withoutEpisodes.map((channel) => (
        <ChannelRow
          key={channel.id}
          channel={channel}
          onEmpty={handleEmpty}
          onEdit={setEditChannel}
          onDelete={setDeleteChannel}
        />
      ))}
      {channels.length === 0 && (
        <p className="text-center text-muted-foreground py-12">
          No channels yet. Create one to get started.
        </p>
      )}

      {/* Render dialogs in a portal to avoid Radix ref conflicts with episode cards */}
      {editChannel &&
        createPortal(
          <EditChannel
            key={editChannel.id}
            channel={editChannel}
            externalOpen
            onExternalClose={() => setEditChannel(null)}
          />,
          document.body,
        )}

      {deleteChannel &&
        createPortal(
          <DeleteChannel
            key={deleteChannel.id}
            id={deleteChannel.id}
            externalOpen
            onExternalClose={() => setDeleteChannel(null)}
          />,
          document.body,
        )}
    </div>
  )
}
