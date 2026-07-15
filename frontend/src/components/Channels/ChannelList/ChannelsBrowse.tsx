// TODO: Validate
import { useQueries, useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { ChevronLeft, ChevronRight, Pencil, Trash2 } from "lucide-react"
import { useRef, useState } from "react"
import { createPortal } from "react-dom"

import { getChannelEpisodes } from "@/api/channels"
import {
  type ChannelOutput,
  type ChannelPublicOutput,
  ChannelsService,
} from "@/client"
import { ChannelDescription } from "@/components/Channels/ChannelDetail/ChannelDescription"
import type { EpisodeWithDetails } from "@/components/Channels/ChannelDetail/columns"
import { EpisodeCard } from "@/components/Channels/ChannelDetail/EpisodeCards"
import { EditChannelDialog } from "@/components/Channels/EditChannelDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import useAuth from "@/hooks/useAuth"
import { ManageShowsButton } from "../ChannelDetail/AddUrlsToQueueButton"
import { ChannelShowsButton } from "./ChannelShowsButton"
import DeleteChannel from "./DeleteChannel"
import EditChannel from "./EditChannel"

// Owner channels (full ChannelOutput) render edit controls; public channels
// (ChannelPublicOutput) are read-only and only need the display fields both share.
type BrowseChannel = ChannelOutput | ChannelPublicOutput

interface ChannelRowProps {
  channel: BrowseChannel
  onDelete: (channel: BrowseChannel) => void
  readOnly?: boolean
  showCreatedBy?: boolean
  showChannelNumber?: boolean
}

function AdminEditChannel({ channel }: { channel: ChannelPublicOutput }) {
  const [open, setOpen] = useState(false)
  const { data: fullChannel } = useQuery({
    queryKey: ["channels", channel.id, "admin-edit"],
    queryFn: () => ChannelsService.getChannel({ channelId: channel.id }),
    enabled: open,
  })

  return (
    <>
      <TooltipIconButton
        label="Edit Channel"
        icon={<Pencil className="size-4" />}
        onClick={() => setOpen(true)}
      />
      {open && fullChannel && (
        <EditChannelDialog
          channel={{ ...fullChannel, username: channel.username }}
          open={open}
          onOpenChange={setOpen}
        />
      )}
    </>
  )
}

function ChannelRow({
  channel,
  onDelete,
  readOnly = false,
  showCreatedBy = true,
  showChannelNumber = true,
}: ChannelRowProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [showLeftArrow, setShowLeftArrow] = useState(false)
  const [showRightArrow, setShowRightArrow] = useState(true)
  const { user } = useAuth()
  const isAdmin = user?.is_superuser ?? false

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
      const channel = data!.channels[episode.channel_id]
      return { ...episode, season, show, source, plugin, channel }
    },
  )

  return (
    <div className="group/row relative">
      <div className="flex items-center gap-3 mb-2 px-[4%]">
        {showChannelNumber && channel.channel_number != null && (
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
          {readOnly ? (
            <>
              <ChannelDescription channel={channel} />
              <ChannelShowsButton channelId={channel.id} />
              {isAdmin && (
                <AdminEditChannel channel={channel as ChannelPublicOutput} />
              )}
            </>
          ) : (
            <>
              {/* Reachable only when !readOnly, where channel is the owner's ChannelOutput. */}
              <ChannelDescription channel={channel} />
              <ManageShowsButton channelId={channel.id} variant="icon" />
              <EditChannel channel={channel as ChannelOutput} />
              <TooltipIconButton
                label="Delete Channel"
                icon={<Trash2 className="size-4 text-destructive" />}
                onClick={() => onDelete(channel)}
              />
            </>
          )}
        </div>
      </div>

      {readOnly && showCreatedBy && channel.user_id && (
        <p className="px-[4%] mb-2 text-sm text-muted-foreground">
          Created by{" "}
          <Link
            to="/users/$userId/channels"
            params={{ userId: channel.user_id }}
            className="underline hover:text-foreground"
          >
            {(channel as ChannelPublicOutput).username || "Unnamed User"}
          </Link>
        </p>
      )}

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
  channels: BrowseChannel[]
  readOnly?: boolean
  showCreatedBy?: boolean
  showChannelNumber?: boolean
}

export function ChannelsBrowse({
  channels,
  readOnly = false,
  showCreatedBy = true,
  showChannelNumber = true,
}: ChannelsBrowseProps) {
  // Public (read-only) lists arrive already ordered by the server (score then id),
  // so preserve that order. Owner lists are sorted by channel number locally.
  const sorted = readOnly
    ? channels
    : [...channels].sort((a, b) => {
        const numA = a.channel_number ?? Number.MAX_SAFE_INTEGER
        const numB = b.channel_number ?? Number.MAX_SAFE_INTEGER
        if (numA !== numB) return numA - numB
        return (a.name ?? "").localeCompare(b.name ?? "")
      })
  const [deleteChannel, setDeleteChannel] = useState<BrowseChannel | null>(null)

  return (
    <div className="flex flex-col gap-8 pb-8">
      {sorted.map((channel) => (
        <ChannelRow
          key={channel.id}
          channel={channel}
          onDelete={setDeleteChannel}
          readOnly={readOnly}
          showCreatedBy={showCreatedBy}
          showChannelNumber={showChannelNumber}
        />
      ))}
      {channels.length === 0 && (
        <p className="text-center text-muted-foreground py-12">
          No channels yet. Create one to get started.
        </p>
      )}

      {/* Render dialogs in a portal to avoid Radix ref conflicts with episode cards */}
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
