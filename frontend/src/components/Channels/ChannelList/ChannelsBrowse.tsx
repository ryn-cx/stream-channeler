// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { ChevronLeft, ChevronRight, Pencil, Trash2 } from "lucide-react"
import { useRef, useState } from "react"
import { createPortal } from "react-dom"

import { getChannelEpisodes } from "@/api/channels"
import {
  type ChannelListOutput,
  type ChannelOutput,
  ChannelsService,
} from "@/client"
import { ChannelDescription } from "@/components/Channels/ChannelDetail/ChannelDescription"
import type { EpisodeWithDetails } from "@/components/Channels/ChannelDetail/columns"
import { EpisodeCard } from "@/components/Channels/ChannelDetail/EpisodeCards"
import { EditChannelDialog } from "@/components/Channels/EditChannelDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import { ManageShowsButton } from "../ChannelDetail/AddUrlsToQueueButton"
import { ChannelShowsButton } from "./ChannelShowsButton"
import DeleteChannel from "./DeleteChannel"
import EditChannel from "./EditChannel"
import EditFavoriteChannel from "./EditFavoriteChannel"
import { FavoriteChannel } from "./FavoriteChannel"

// Owner channels (full ChannelOutput) render edit controls; public channels
// (ChannelListOutput) are read-only and only need the display fields both share.
export type BrowseChannel = ChannelOutput | ChannelListOutput

interface ChannelRowProps {
  channel: BrowseChannel
  onDelete: (channel: BrowseChannel) => void
  readOnly?: boolean
  showCreatedBy?: boolean
  showChannelNumber?: boolean
  // In the favorites view, offer the viewer's private customization (name/number/
  // icon) and an extra edit button to change it.
  personalizable?: boolean
}

function AdminEditChannel({ channel }: { channel: ChannelListOutput }) {
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
  personalizable = false,
}: ChannelRowProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [showLeftArrow, setShowLeftArrow] = useState(false)
  const [showRightArrow, setShowRightArrow] = useState(true)
  const { user } = useAuth()
  const isAdmin = user?.is_superuser ?? false
  const isOwner = user?.id === channel.user_id
  const loggedIn = isLoggedIn()

  // A favorited channel can carry the viewer's private name/number, which are
  // preferred over the channel's own values. They only arrive in the favorites
  // scope, so elsewhere these fall back to the shared channel.
  const listChannel = channel as ChannelListOutput
  const displayName = listChannel.custom_name ?? channel.name
  const displayNumber =
    listChannel.custom_channel_number ?? channel.channel_number

  const defaultOrder = channel.default_order
    ? (() => {
        try {
          return JSON.parse(channel.default_order)
        } catch {
          return {}
        }
      })()
    : {}

  const hasDefaultOrder = Object.keys(defaultOrder).length > 0

  const orderedQuery = useQuery({
    queryKey: ["episodes-preview", channel.id, defaultOrder],
    queryFn: () =>
      getChannelEpisodes({
        channelId: channel.id,
        limit: 20,
        ...defaultOrder,
      }),
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    retry: false,
  })

  // A saved default order can be rejected by the API when it was stored under an
  // older schema, so retry without any options rather than losing the whole row.
  const orderRejected = orderedQuery.isError && hasDefaultOrder
  const fallbackQuery = useQuery({
    queryKey: ["episodes-preview", channel.id, "no-options"],
    queryFn: () => getChannelEpisodes({ channelId: channel.id, limit: 20 }),
    enabled: orderRejected,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    retry: false,
  })

  const query = orderRejected ? fallbackQuery : orderedQuery
  const data = query.data
  const isLoading =
    orderedQuery.isPending || (orderRejected && fallbackQuery.isPending)
  const loadFailed = orderRejected
    ? fallbackQuery.isError
    : orderedQuery.isError

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
        {showChannelNumber && displayNumber != null && (
          <span className="text-2xl font-bold text-muted-foreground tabular-nums">
            {displayNumber}
          </span>
        )}
        <Link
          to="/channels/$channelId"
          params={{ channelId: channel.id }}
          search={defaultOrder}
          className="text-2xl font-bold hover:text-primary transition-colors"
        >
          {displayName}
        </Link>
        <div className="flex">
          {readOnly ? (
            <>
              <ChannelDescription channel={channel} />
              <ChannelShowsButton channelId={channel.id} />
              {loggedIn && <FavoriteChannel channelId={channel.id} />}
              {personalizable && loggedIn && (
                <EditFavoriteChannel channel={listChannel} />
              )}
              {(isAdmin || isOwner) && (
                <AdminEditChannel channel={channel as ChannelListOutput} />
              )}
            </>
          ) : (
            <>
              {/* Reachable only when !readOnly, where channel is the owner's ChannelOutput. */}
              <ChannelDescription channel={channel} />
              <ManageShowsButton channelId={channel.id} variant="icon" />
              {loggedIn && <FavoriteChannel channelId={channel.id} />}
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

      {showCreatedBy &&
        (readOnly ? (
          // The API hands the real creator of an anonymous channel to admins and
          // the owner, but a public listing must still present it anonymously, so
          // the creator is hidden whenever the channel is anonymous.
          channel.user_id &&
          !channel.anonymous && (
            <p className="px-[4%] mb-2 text-sm text-muted-foreground">
              Created by{" "}
              <Link
                to="/users/$userId/channels"
                params={{ userId: channel.user_id }}
                className="underline hover:text-foreground"
              >
                {(channel as ChannelListOutput).username}
              </Link>
            </p>
          )
        ) : // On the owner's own channels, mirror how others will see it: a private
        // channel isn't visible to anyone else so it shows nothing, and an
        // anonymous channel hides the creator's name.
        channel.visibility === "private" ? null : (
          <p className="px-[4%] mb-2 text-sm text-muted-foreground">
            Created by {channel.anonymous ? "Anonymous" : user?.username}
          </p>
        ))}

      {orderRejected && !loadFailed && (
        <p className="px-[4%] mb-2 text-sm text-destructive">
          This channel's saved order could not be applied, so its episodes are
          unsorted.
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

          {!isLoading && loadFailed && (
            <p className="text-sm text-destructive py-8">
              Could not load episodes for this channel.
            </p>
          )}

          {!isLoading && !loadFailed && episodesWithDetails.length === 0 && (
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
  personalizable?: boolean
}

// Default channel-list order: by channel number ascending. Favorites prefer the
// viewer's own `custom_channel_number`, and a channel with no number is treated as
// 999 so it sorts after the numbered ones.
export function sortChannelsByNumber<T extends BrowseChannel>(
  channels: T[],
): T[] {
  const effectiveNumber = (channel: T): number => {
    const listChannel = channel as ChannelListOutput
    return listChannel.custom_channel_number ?? channel.channel_number ?? 999
  }
  return [...channels].sort((first, second) => {
    const firstNumber = effectiveNumber(first)
    const secondNumber = effectiveNumber(second)
    if (firstNumber !== secondNumber) return firstNumber - secondNumber
    return (first.name ?? "").localeCompare(second.name ?? "")
  })
}

export function ChannelsBrowse({
  channels,
  readOnly = false,
  showCreatedBy = true,
  showChannelNumber = true,
  personalizable = false,
}: ChannelsBrowseProps) {
  const [deleteChannel, setDeleteChannel] = useState<BrowseChannel | null>(null)

  return (
    <div className="flex flex-col gap-8 pb-8">
      {channels.map((channel) => (
        <ChannelRow
          key={channel.id}
          channel={channel}
          onDelete={setDeleteChannel}
          readOnly={readOnly}
          showCreatedBy={showCreatedBy}
          showChannelNumber={showChannelNumber}
          personalizable={personalizable}
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
