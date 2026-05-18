// TODO: Validate
import { useQuery, useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { EllipsisVertical, LayoutGrid, Table as TableIcon } from "lucide-react"
import { Suspense, useEffect, useState } from "react"
import { getChannelEpisodes } from "@/api/channels"
import { ChannelsService, type SortKeyInput } from "@/client"
import { ManageShowsButton } from "@/components/Channels/ChannelDetail/AddUrlsToQueueButton"
import {
  columns,
  type EpisodeWithDetails,
} from "@/components/Channels/ChannelDetail/columns"
import { EpisodeCards } from "@/components/Channels/ChannelDetail/EpisodeCards"
import { EpisodeFilters } from "@/components/Channels/ChannelDetail/EpisodeFilters"
import { ManageAdditionalChannels } from "@/components/Channels/ChannelDetail/ManageSubChannels"
import { SaveDefaultButton } from "@/components/Channels/ChannelDetail/SaveDefaultButton"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import PendingChannelDetails from "@/components/Pending/PendingChannelDetails"
import { EditOrderButton } from "@/components/PlaylistChannelCommon/EditOrderButton"
import { HeroBillboard } from "@/components/PlaylistChannelCommon/HeroBillboard"
import { SaveAsPlaylistButton } from "@/components/Playlists/PlaylistDetail/SaveAsPlaylistButton"
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
  sortBy?: Array<SortKeyInput>
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
  additionalChannels?: string[]
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
      sortBy: search.sortBy as ChannelSearchParams["sortBy"],
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
      additionalChannels: search.additionalChannels as string[] | undefined,
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

function ChannelDetailContent({ channelId }: { channelId: string }) {
  const { user } = useAuth()
  const { data: channel } = useSuspenseQuery(getChannelQueryOptions(channelId))
  const watchedMutation = useMarkWatched(channelId)

  useEffect(() => {
    document.title = `${channel.name} - Stream Channeler`
  }, [channel.name])

  const search = Route.useSearch()
  const { data: episodesData, isPlaceholderData } = useQuery(
    getEpisodesQueryOptions(channelId, search),
  )
  const routeFullPath = Route.fullPath

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

  const currentChannelIds = search.additionalChannels
    ? [channelId, ...search.additionalChannels]
    : [channelId]

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
      {/* Hero billboard */}
      {showHero && heroEpisode && (
        <HeroBillboard
          episode={heroEpisode}
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
      )}

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2 px-[4%] py-4">
        <h1 className="text-2xl font-bold tracking-tight mr-2">
          {channel.name}
        </h1>

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

              {isOwner && (
                <>
                  <DropdownMenuSeparator />
                  <ManageShowsButton channelId={channelId} variant="menu" />
                </>
              )}
              <DropdownMenuSeparator />
              <ManageAdditionalChannels
                channelId={channelId}
                filterParams={search}
                routeFullPath={routeFullPath}
                currentChannelIds={currentChannelIds}
                isLoggedIn={!!user}
                variant="menu"
              />

              <EpisodeFilters
                filterParams={search}
                routeFullPath={routeFullPath}
                channelId={channelId}
                randomSeed={search.randomSeed}
                variant="menu"
              />

              {isOwner && (
                <SaveDefaultButton
                  channelId={channelId}
                  searchParams={search}
                  variant="menu"
                />
              )}
              <SaveAsPlaylistButton
                episodes={episodesData?.episodes ?? []}
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
              className="mt-2 mb-4"
            >
              <TableIcon />
              Table
            </Button>
          ) : (
            <Button
              variant="outline"
              onClick={() => setViewMode("cards")}
              title="Switch to card view"
              className="mt-2 mb-4"
            >
              <LayoutGrid />
              Cards
            </Button>
          )}
          {isOwner && <ManageShowsButton channelId={channelId} />}
          <ManageAdditionalChannels
            channelId={channelId}
            filterParams={search}
            routeFullPath={routeFullPath}
            currentChannelIds={currentChannelIds}
            isLoggedIn={!!user}
          />
          <EpisodeFilters
            filterParams={search}
            routeFullPath={routeFullPath}
            channelId={channelId}
            randomSeed={search.randomSeed}
          />
          {isOwner && (
            <SaveDefaultButton channelId={channelId} searchParams={search} />
          )}
          <SaveAsPlaylistButton episodes={episodesData?.episodes ?? []} />
          {viewMode === "cards" && (
            <EditOrderButton
              editOrder={editOrder}
              onToggle={() => setEditOrder(!editOrder)}
            />
          )}
          {viewMode === "table" && <ColumnVisibilityButton table={table} />}
        </div>
      </div>

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
            hideWatched={search.hideWatched}
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
