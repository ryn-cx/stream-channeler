// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import {
  ChevronLeft,
  ChevronRight,
  Loader2,
  Pencil,
  Star,
  Trash2,
} from "lucide-react"
import { useEffect, useMemo, useRef, useState } from "react"
import { createPortal } from "react-dom"

import { getChannelEpisodes } from "@/api/channels"
import {
  type ChannelListOutput,
  type ChannelOutput,
  ChannelsService,
} from "@/client"
import { ChannelCreatedBy } from "@/components/Channels/ChannelCreatedBy"
import type { EpisodeWithDetails } from "@/components/Channels/ChannelDetail/columns"
import { EpisodeCard } from "@/components/Channels/ChannelDetail/EpisodeCards"
import { EditChannelDialog } from "@/components/Channels/EditChannelDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import { ManageShowsButton } from "../ChannelDetail/AddUrlsToQueueButton"
import { ChannelDetailsButton } from "./ChannelDetailsButton"
import DeleteChannel from "./DeleteChannel"
import EditChannel from "./EditChannel"
import EditFavoriteChannel from "./EditFavoriteChannel"
import {
  readEpisodePreview,
  writeChannelDetails,
  writeEpisodePreview,
} from "./episodePreviewCache"
import { FavoriteChannel, useFavoriteChannelIds } from "./FavoriteChannel"

// Owner channels (full ChannelOutput) render edit controls; public channels
// (ChannelListOutput) are read-only and only need the display fields both share.
export type BrowseChannel = ChannelOutput | ChannelListOutput

// Whether every channel-row button spells its label out rather than relying on
// its tooltip. Flip this one value to switch the whole row either way.
const SHOW_BUTTON_LABELS = true

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

// TODO: Validate
function AdminEditChannel({
  channel,
  showLabel,
}: {
  channel: ChannelListOutput
  showLabel?: boolean
}) {
  const [open, setOpen] = useState(false)
  const { data: fullChannel } = useQuery({
    queryKey: ["channels", channel.id, "admin-edit"],
    queryFn: () => ChannelsService.getChannel({ channelId: channel.id }),
    enabled: open,
  })

  return (
    <>
      <TooltipIconButton
        label="Edit channel"
        icon={<Pencil className="size-4" />}
        onClick={() => setOpen(true)}
        showLabel={showLabel}
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

// TODO: Validate
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
  const isFavorite = useFavoriteChannelIds().has(channel.id)

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

  const cachedPreview = useMemo(
    () => readEpisodePreview(channel.id),
    [channel.id],
  )

  useEffect(() => {
    writeChannelDetails(channel as ChannelOutput)
  }, [channel])
  const orderedQuery = useQuery({
    queryKey: ["episodes-preview", channel.id, defaultOrder],
    queryFn: async () => {
      const preview = await getChannelEpisodes({
        channelId: channel.id,
        limit: 20,
        ...defaultOrder,
      })
      writeEpisodePreview(channel.id, preview)
      return preview
    },
    initialData: cachedPreview,
    initialDataUpdatedAt: 0,
    staleTime: 300_000,
    refetchOnWindowFocus: false,
    retry: false,
  })

  // A saved default order can be rejected by the API when it was stored under an
  // older schema, so retry without any options rather than losing the whole row.
  const orderRejected = orderedQuery.isError && hasDefaultOrder
  const fallbackQuery = useQuery({
    queryKey: ["episodes-preview", channel.id, "no-options"],
    queryFn: async () => {
      const preview = await getChannelEpisodes({
        channelId: channel.id,
        limit: 10,
      })
      writeEpisodePreview(channel.id, preview)
      return preview
    },
    enabled: orderRejected,
    staleTime: 300_000,
    refetchOnWindowFocus: false,
    retry: false,
  })

  const query = orderRejected ? fallbackQuery : orderedQuery
  const data = query.data
  const isLoading =
    orderedQuery.isPending || (orderRejected && fallbackQuery.isPending)
  const isRefreshing = query.isFetching && data !== undefined
  const loadFailed = orderRejected
    ? fallbackQuery.isError
    : orderedQuery.isError

  // TODO: Validate
  const updateArrows = () => {
    const container = scrollRef.current
    if (!container) return
    setShowLeftArrow(container.scrollLeft > 10)
    setShowRightArrow(
      container.scrollLeft < container.scrollWidth - container.clientWidth - 10,
    )
  }

  // TODO: Validate
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
      {/* Block flow rather than a flex row, so a title that wraps starts its
          later lines at the gutter instead of indenting past the star. */}
      <div className="mb-2 px-[4%] text-2xl font-bold wrap-break-word">
        {(isFavorite || (showChannelNumber && displayNumber != null)) && (
          <span className="mr-3 whitespace-nowrap text-muted-foreground tabular-nums">
            {isFavorite && (
              <Star className="inline size-6 align-text-bottom fill-yellow-400 text-yellow-400" />
            )}
            {isFavorite && showChannelNumber && displayNumber != null && " "}
            {showChannelNumber && displayNumber != null && `${displayNumber}.`}
          </span>
        )}
        <Link
          to="/channels/$channelId"
          params={{ channelId: channel.id }}
          search={defaultOrder}
          className="hover:text-primary transition-colors"
        >
          {displayName}
        </Link>
        {isRefreshing && (
          <Loader2
            className="ml-2 inline size-5 animate-spin align-text-bottom text-muted-foreground"
            aria-label="Checking for newer episodes"
          />
        )}
      </div>

      {showCreatedBy && (
        <ChannelCreatedBy channel={channel} className="px-[4%] mb-2" />
      )}

      <div className="flex flex-wrap gap-2 px-[4%] mb-2">
        {loggedIn && (
          <FavoriteChannel
            channelId={channel.id}
            showLabel={SHOW_BUTTON_LABELS}
          />
        )}
        {readOnly ? (
          <>
            {isAdmin && (
              <ManageShowsButton
                channelId={channel.id}
                channelName={channel.name}
                variant="icon"
                showLabel={SHOW_BUTTON_LABELS}
              />
            )}
            <ChannelDetailsButton
              channel={channel}
              showLabel={SHOW_BUTTON_LABELS}
            />
            {personalizable && loggedIn && (
              <EditFavoriteChannel
                channel={listChannel}
                showLabel={SHOW_BUTTON_LABELS}
              />
            )}
            {(isAdmin || isOwner) && (
              <AdminEditChannel
                channel={channel as ChannelListOutput}
                showLabel={SHOW_BUTTON_LABELS}
              />
            )}
          </>
        ) : (
          <>
            {/* Reachable only when !readOnly, where channel is the owner's ChannelOutput. */}
            <ChannelDetailsButton
              channel={channel}
              showLabel={SHOW_BUTTON_LABELS}
            />
            <ManageShowsButton
              channelId={channel.id}
              channelName={channel.name}
              variant="icon"
              showLabel={SHOW_BUTTON_LABELS}
            />
            <EditChannel
              channel={channel as ChannelOutput}
              showLabel={SHOW_BUTTON_LABELS}
            />
            <TooltipIconButton
              label="Delete channel"
              icon={<Trash2 className="size-4 text-destructive" />}
              onClick={() => onDelete(channel)}
              showLabel={SHOW_BUTTON_LABELS}
            />
          </>
        )}
      </div>

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
// TODO: Validate
export function sortChannelsByNumber<T extends BrowseChannel>(
  channels: T[],
): T[] {
  // TODO: Validate
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

// TODO: Validate
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
