// TODO: Validate
import { useQuery, useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, Link, redirect } from "@tanstack/react-router"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { EllipsisVertical, LayoutGrid, Table as TableIcon } from "lucide-react"
import { Suspense, useEffect, useState } from "react"
import { getChannelEpisodes } from "@/api/channels"
import {
  ChannelOrdersService,
  ChannelsService,
  type SortKeyInput,
} from "@/client"
import { EditOrderButton } from "@/components/ChannelCommon/EditOrderButton"
import { HeroBillboard } from "@/components/ChannelCommon/HeroBillboard"
import { LastWatchedBadge } from "@/components/ChannelCommon/LastWatchedBadge"
import { useEpisodeActions } from "@/components/ChannelCommon/useEpisodeActions"
import { ManageShowsButton } from "@/components/Channels/ChannelDetail/AddUrlsToQueueButton"
import { ChannelDescription } from "@/components/Channels/ChannelDetail/ChannelDescription"
import { CommentsDialog } from "@/components/Channels/ChannelDetail/CommentsDialog"
import {
  columns,
  type EpisodeWithDetails,
} from "@/components/Channels/ChannelDetail/columns"
import { EpisodeCards } from "@/components/Channels/ChannelDetail/EpisodeCards"
import { EpisodeFilters } from "@/components/Channels/ChannelDetail/EpisodeFilters"
import { SaveOrderButton } from "@/components/Channels/ChannelDetail/SaveOrderButton"
import { ChannelShowsButton } from "@/components/Channels/ChannelList/ChannelShowsButton"
import EditChannel from "@/components/Channels/ChannelList/EditChannel"
import { FavoriteChannel } from "@/components/Channels/ChannelList/FavoriteChannel"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import PendingChannelDetails from "@/components/Pending/PendingChannelDetails"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Skeleton } from "@/components/ui/skeleton"
import useAuth from "@/hooks/useAuth"
import { useMarkWatched } from "@/hooks/useMarkEpisodeWatched"
import { usePersistedState } from "@/hooks/usePersistedState"
import { parseOrderConfig } from "@/lib/channelOrder"
import type { WatchFilters } from "@/lib/watchFilters"

function getChannelQueryOptions(channelId: string) {
  return {
    queryFn: () => ChannelsService.getChannel({ channelId }),
    queryKey: ["channels", channelId],
    refetchOnWindowFocus: false,
    refetchOnMount: false,
  }
}

type ChannelSearchParams = {
  hideWatched?: boolean
  hideUnwatched?: boolean
  hidePartiallyWatched?: boolean
  sortBy?: Array<SortKeyInput>
  orderPresetId?: string
  maximumWatchDate?: string
  totalShowsCount?: number
  startedShowsCount?: number
  newShowsCount?: number
  minimumAirDate?: string
  maximumAirDate?: string
  minimumReleaseDate?: string
  maximumReleaseDate?: string
  minimumDuration?: number
  maximumDuration?: number
  limit?: number
  sourceIds?: string[]
  sourceIdsIsBlacklist?: boolean
  randomSeed?: number
}

export const Route = createFileRoute("/_layout/channels/$channelId")({
  component: ChannelDetail,
  beforeLoad: async ({ params }) => {
    // Check if the user can access this channel
    try {
      await ChannelsService.getChannel({ channelId: params.channelId })
    } catch (error: any) {
      // If 401 or 403, user doesn't have access to this channel
      if (error?.status === 401 || error?.status === 403) {
        throw redirect({ to: "/" })
      }
      // Re-throw other errors (404, network errors, etc.)
      throw error
    }
  },
  validateSearch: (search: Record<string, unknown>): ChannelSearchParams => {
    return {
      hideWatched: search.hideWatched as boolean | undefined,
      hideUnwatched: search.hideUnwatched as boolean | undefined,
      hidePartiallyWatched: search.hidePartiallyWatched as boolean | undefined,
      sortBy: search.sortBy as ChannelSearchParams["sortBy"],
      orderPresetId: search.orderPresetId as string | undefined,
      maximumWatchDate: search.maximumWatchDate as string | undefined,
      totalShowsCount: search.totalShowsCount as number | undefined,
      startedShowsCount: search.startedShowsCount as number | undefined,
      newShowsCount: search.newShowsCount as number | undefined,
      minimumAirDate: search.minimumAirDate as string | undefined,
      maximumAirDate: search.maximumAirDate as string | undefined,
      minimumReleaseDate: search.minimumReleaseDate as string | undefined,
      maximumReleaseDate: search.maximumReleaseDate as string | undefined,
      minimumDuration: search.minimumDuration as number | undefined,
      maximumDuration: search.maximumDuration as number | undefined,
      limit: search.limit as number | undefined,
      sourceIds: search.sourceIds as string[] | undefined,
      sourceIdsIsBlacklist: search.sourceIdsIsBlacklist as boolean | undefined,
      randomSeed: search.randomSeed as number | undefined,
    }
  },
  head: () => ({
    meta: [
      {
        title: "Channel - Stream Channeler",
      },
    ],
  }),
})

function getEpisodesQueryOptions(
  channelId: string,
  searchParams: ChannelSearchParams,
) {
  return {
    queryFn: () =>
      getChannelEpisodes({
        channelId,
        ...searchParams,
      }),
    queryKey: ["episodes", channelId, searchParams],
    refetchOnWindowFocus: false,
    placeholderData: (previousData: any) => previousData,
  }
}

type ViewMode = "table" | "cards"

/** Wraps the billboard so the episode action hook only runs when there is a
 * hero episode to act on. */
function HeroWithActions({
  episode,
  channelId,
  watchFilters,
  ...heroProps
}: {
  episode: EpisodeWithDetails
  channelId: string
  watchFilters?: WatchFilters
  onPlay: () => void
  onSkip: () => void
  onBack: () => void
  hasNext: boolean
  hasPrev: boolean
}) {
  const { menuItems, dialogs } = useEpisodeActions({
    episode,
    channelId,
    watchFilters,
  })

  return (
    <>
      <HeroBillboard
        episode={episode}
        menuItems={menuItems}
        topLeftBadge={
          episode.watch_date ? <LastWatchedBadge episode={episode} /> : null
        }
        {...heroProps}
      />
      {dialogs}
    </>
  )
}

function ChannelDetailContent({ channelId }: { channelId: string }) {
  const { user } = useAuth()
  const { data: channel } = useSuspenseQuery(getChannelQueryOptions(channelId))

  useEffect(() => {
    document.title = `${channel.name} - Stream Channeler`
  }, [channel.name])

  const search = Route.useSearch()
  const { data: episodesData, isPlaceholderData } = useQuery(
    getEpisodesQueryOptions(channelId, search),
  )
  const routeFullPath = Route.fullPath

  // A referenced preset holds the options the backend actually applies, and the URL
  // only carries its id, so the preset has to be read back for the dialog to show it.
  const { data: orderPreset } = useQuery({
    queryKey: ["channel-orders", search.orderPresetId],
    queryFn: () =>
      ChannelOrdersService.getChannelOrder({
        channelOrderId: search.orderPresetId as string,
      }),
    enabled: search.orderPresetId !== undefined,
    refetchOnWindowFocus: false,
  })

  // `_resolve_order_preset` overrides the channel's options with every option the
  // preset stored, so the preset wins here the same way it does on the backend.
  const filterParams: ChannelSearchParams = orderPreset
    ? {
        ...search,
        ...(parseOrderConfig(
          orderPreset.config,
        ) as Partial<ChannelSearchParams>),
      }
    : search

  const watchedMutation = useMarkWatched(channelId, filterParams)

  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({
    id: false,
    plugin: false,
  })
  const [viewMode, setViewMode] = usePersistedState<ViewMode>(
    "channel-detail-view",
    "cards",
  )
  const [editOrderFlag, setEditOrderFlag] = usePersistedState<"on" | "off">(
    `channel-detail-edit-order:${channelId}`,
    "off",
  )
  const editOrder = editOrderFlag === "on"
  const setEditOrder = (next: boolean) => setEditOrderFlag(next ? "on" : "off")

  const episodesWithDetails: EpisodeWithDetails[] = (
    episodesData?.episodes ?? []
  ).map((episode) => {
    const season = episodesData!.seasons[episode.season_id]
    const show = episodesData!.shows[season.show_id]
    const source = episodesData!.sources[show.source_id]
    const plugin = episodesData!.plugins[source.plugin_id]
    const channel = episodesData!.channels[episode.channel_id]
    return { ...episode, season, show, source, plugin, channel }
  })

  // From: https://tanstack.com/table/v8/docs/framework/react/examples/column-visibility
  const table = useReactTable({
    data: episodesWithDetails,
    columns,
    state: {
      columnVisibility,
    },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  const isOwner = user?.id === channel.user_id
  const showHero = viewMode === "cards" && episodesWithDetails.length > 0
  const [heroIndex, setHeroIndex] = useState(0)

  const heroEpisode = episodesWithDetails[heroIndex] ?? episodesWithDetails[0]
  const hasNextHero = heroIndex < episodesWithDetails.length - 1
  const hasPrevHero = heroIndex > 0

  return (
    <div className="flex flex-col">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2 px-[4%] py-4">
        {user && <FavoriteChannel channelId={channel.id} />}

        <div className="mr-2">
          <h1 className="text-2xl font-bold tracking-tight">{channel.name}</h1>
          {/* The API only sends a username when the owner is public, so an
              anonymous channel simply has nothing to show here. */}
          {channel.username && channel.user_id && (
            <p className="text-xs text-muted-foreground">
              by{" "}
              <Link
                to="/users/$userId/channels"
                params={{ userId: channel.user_id }}
                className="underline hover:text-foreground"
              >
                {channel.username}
              </Link>
            </p>
          )}
        </div>

        <ChannelDescription channel={channel} />

        {(isOwner || user?.is_superuser) && <EditChannel channel={channel} />}

        {/* Smaller screens: Use a hamburger menu */}
        <div className="xl:hidden">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="icon">
                <EllipsisVertical className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-56">
              {viewMode === "cards" ? (
                <DropdownMenuItem onClick={() => setViewMode("table")}>
                  <TableIcon className="mr-2 size-4" />
                  Table View
                </DropdownMenuItem>
              ) : (
                <DropdownMenuItem onClick={() => setViewMode("cards")}>
                  <LayoutGrid className="mr-2 size-4" />
                  Card View
                </DropdownMenuItem>
              )}

              {viewMode === "table" && (
                <>
                  <DropdownMenuSeparator />
                  <ColumnVisibilityButton table={table} variant="menu" />
                </>
              )}

              <DropdownMenuSeparator />
              {isOwner ? (
                <ManageShowsButton
                  channelId={channelId}
                  variant="menu"
                  combinedChannels={{ isLoggedIn: !!user }}
                />
              ) : (
                <ChannelShowsButton channelId={channelId} variant="menu" />
              )}
              <DropdownMenuSeparator />

              <EpisodeFilters
                key={orderPreset?.id ?? "channel"}
                filterParams={filterParams}
                routeFullPath={routeFullPath}
                channelId={channelId}
                randomSeed={filterParams.randomSeed}
                variant="menu"
                isOwner={isOwner}
              />

              {viewMode === "cards" && (
                <EditOrderButton
                  editOrder={editOrder}
                  onToggle={() => setEditOrder(!editOrder)}
                  variant="menu"
                />
              )}

              {isOwner && viewMode === "cards" && editOrder && (
                <SaveOrderButton
                  channelId={channelId}
                  episodes={episodesData?.episodes ?? []}
                  variant="menu"
                />
              )}

              <DropdownMenuSeparator />
              <CommentsDialog
                channelId={channelId}
                channelName={channel?.name}
                variant="menu"
              />
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* Larger screens: Show all buttons */}
        <div className="hidden xl:flex flex-wrap gap-2">
          {viewMode === "cards" ? (
            <Button
              variant="outline"
              onClick={() => setViewMode("table")}
              title="Switch to table view"
            >
              <TableIcon />
              Table
            </Button>
          ) : (
            <Button
              variant="outline"
              onClick={() => setViewMode("cards")}
              title="Switch to card view"
            >
              <LayoutGrid />
              Cards
            </Button>
          )}
          {isOwner ? (
            <ManageShowsButton
              channelId={channelId}
              combinedChannels={{ isLoggedIn: !!user }}
            />
          ) : (
            <ChannelShowsButton channelId={channelId} variant="button" />
          )}
          <EpisodeFilters
            key={orderPreset?.id ?? "channel"}
            filterParams={filterParams}
            routeFullPath={routeFullPath}
            channelId={channelId}
            randomSeed={filterParams.randomSeed}
            isOwner={isOwner}
          />
          {viewMode === "cards" && (
            <EditOrderButton
              editOrder={editOrder}
              onToggle={() => setEditOrder(!editOrder)}
            />
          )}
          {isOwner && viewMode === "cards" && editOrder && (
            <SaveOrderButton
              channelId={channelId}
              episodes={episodesData?.episodes ?? []}
            />
          )}
          {viewMode === "table" && <ColumnVisibilityButton table={table} />}
          <CommentsDialog channelId={channelId} channelName={channel?.name} />
        </div>
      </div>

      {/* Hero billboard - inset to line up with the card grid below it */}
      {showHero && heroEpisode && (
        <div className="px-[4%] pb-4">
          <div className="overflow-hidden rounded-lg">
            <HeroWithActions
              episode={heroEpisode}
              channelId={channelId}
              watchFilters={filterParams}
              onPlay={() => {
                watchedMutation.mutate(heroEpisode.id)
                if (heroEpisode.url) {
                  window.open(heroEpisode.url, "_blank", "noopener,noreferrer")
                }
                if (hasNextHero) setHeroIndex(heroIndex + 1)
              }}
              onSkip={() => {
                if (hasNextHero) setHeroIndex(heroIndex + 1)
              }}
              onBack={() => {
                if (hasPrevHero) setHeroIndex(heroIndex - 1)
              }}
              hasNext={hasNextHero}
              hasPrev={hasPrevHero}
            />
          </div>
        </div>
      )}

      {/* Content */}
      <div
        className={`px-[4%] transition-opacity duration-200 ${isPlaceholderData ? "opacity-60" : ""}`}
      >
        {!episodesData ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-4">
            {Array.from({ length: 12 }).map((_, i) => (
              <div key={i} className="flex flex-col gap-2">
                <Skeleton className="w-full aspect-video rounded-sm" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-3 w-1/2" />
              </div>
            ))}
          </div>
        ) : viewMode === "table" ? (
          <DataTable
            columns={columns}
            data={episodesWithDetails}
            columnVisibility={columnVisibility}
            onColumnVisibilityChange={setColumnVisibility}
          />
        ) : (
          <EpisodeCards
            episodes={episodesWithDetails}
            channelId={channelId}
            watchFilters={filterParams}
            editOrder={editOrder}
          />
        )}
      </div>
    </div>
  )
}

function ChannelDetail() {
  const { channelId } = Route.useParams()

  // biome-ignore lint/correctness/useExhaustiveDependencies: scroll to top when channel changes
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [channelId])

  return (
    <Suspense fallback={<PendingChannelDetails />}>
      <ChannelDetailContent channelId={channelId} />
    </Suspense>
  )
}
