// TODO: Validate
import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { EllipsisVertical, LayoutGrid, Table as TableIcon } from "lucide-react"
import { Suspense, useState } from "react"

import { ChannelsService } from "@/client"
import { AddUrlsToQueueButton } from "@/components/Channels/ChannelDetail/AddUrlsToQueueButton"
import {
  columns,
  type EpisodeWithDetails,
} from "@/components/Channels/ChannelDetail/columns"
import { EpisodeCards } from "@/components/Channels/ChannelDetail/EpisodeCards"
import { EpisodeFilters } from "@/components/Channels/ChannelDetail/EpisodeFilters"
import { ManageShows } from "@/components/Channels/ChannelDetail/ManageShows"
import { ManageAdditionalChannels } from "@/components/Channels/ChannelDetail/ManageSubChannels"
import { SaveDefaultButton } from "@/components/Channels/ChannelDetail/SaveDefaultButton"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import PendingChannelDetails from "@/components/Pending/PendingChannelDetails"
import { Button } from "@/components/ui/button"
import { ButtonGroup } from "@/components/ui/button-group"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import useAuth from "@/hooks/useAuth"

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
  rotateShows?: boolean
  rotateShowsRandomly?: boolean
  randomizeOnLastSort?: boolean
  sortBy?: string[]
  maximumWatchDate?: string
  onlyStartedShows?: boolean
  onlyNewShows?: boolean
  minimumAirDate?: string
  maximumAirDate?: string
  minimumReleaseDate?: string
  maximumReleaseDate?: string
  minimumDuration?: number
  maximumDuration?: number
  additionalChannels?: string[]
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
      rotateShows: search.rotateShows as boolean | undefined,
      rotateShowsRandomly: search.rotateShowsRandomly as boolean | undefined,
      randomizeOnLastSort: search.randomizeOnLastSort as boolean | undefined,
      sortBy: search.sortBy as string[] | undefined,
      maximumWatchDate: search.maximumWatchDate as string | undefined,
      onlyStartedShows: search.onlyStartedShows as boolean | undefined,
      onlyNewShows: search.onlyNewShows as boolean | undefined,
      minimumAirDate: search.minimumAirDate as string | undefined,
      maximumAirDate: search.maximumAirDate as string | undefined,
      minimumReleaseDate: search.minimumReleaseDate as string | undefined,
      maximumReleaseDate: search.maximumReleaseDate as string | undefined,
      minimumDuration: search.minimumDuration as number | undefined,
      maximumDuration: search.maximumDuration as number | undefined,
      additionalChannels: search.additionalChannels as string[] | undefined,
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
      ChannelsService.getChannelEpisodes({
        channelId,
        ...searchParams,
      }),
    queryKey: ["episodes", channelId],
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    placeholderData: (previousData: any) => previousData,
  }
}

type ViewMode = "table" | "cards"

function ChannelDetailContent({ channelId }: { channelId: string }) {
  const { user } = useAuth()
  const { data: channel } = useSuspenseQuery(getChannelQueryOptions(channelId))
  const search = Route.useSearch()
  const { data: episodesData } = useSuspenseQuery(
    getEpisodesQueryOptions(channelId, search),
  )
  const routeFullPath = Route.fullPath

  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({
    id: false,
    plugin: false,
  })
  const [viewMode, setViewMode] = useState<ViewMode>("cards")

  const currentChannelIds = search.additionalChannels
    ? [channelId, ...search.additionalChannels]
    : [channelId]

  const episodesWithDetails: EpisodeWithDetails[] = episodesData.episodes.map(
    (episode) => {
      const season = episodesData.seasons[episode.season_id]
      const show = episodesData.shows[season.show_id]
      const source = episodesData.sources[show.source_id]
      const plugin = episodesData.plugins[source.plugin_id]
      return { ...episode, season, show, source, plugin }
    },
  )

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
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold tracking-tight">{channel.name}</h1>

          {/* Smaller screens: Use a hamburger menu */}
          <div className="xl:hidden">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="icon">
                  <EllipsisVertical className="size-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-56">
                <DropdownMenuItem onClick={() => setViewMode("table")}>
                  <TableIcon className="mr-2 size-4" />
                  Table View
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setViewMode("cards")}>
                  <LayoutGrid className="mr-2 size-4" />
                  Card View
                </DropdownMenuItem>

                {viewMode === "table" && (
                  <>
                    <DropdownMenuSeparator />
                    <ColumnVisibilityButton table={table} variant="menu" />
                  </>
                )}

                {isOwner && (
                  <>
                    <DropdownMenuSeparator />
                    <AddUrlsToQueueButton
                      channelId={channelId}
                      variant="menu"
                    />
                    <ManageShows channelId={channelId} variant="menu" />
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
                  variant="menu"
                />

                {isOwner && (
                  <SaveDefaultButton
                    channelId={channelId}
                    searchParams={search}
                    variant="menu"
                  />
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        {/* Larger screens: Show all buttons */}
        <div className="hidden xl:flex flex-wrap gap-2">
          <ButtonGroup>
            <Button
              variant={viewMode === "table" ? "default" : "outline"}
              size="icon"
              onClick={() => setViewMode("table")}
              title="Table view"
              className="my-4"
            >
              <TableIcon className="mr-2" />
            </Button>
            <Button
              variant={viewMode === "cards" ? "default" : "outline"}
              size="icon"
              onClick={() => setViewMode("cards")}
              title="Card view"
              className="my-4"
            >
              <LayoutGrid className="mr-2" />
            </Button>
          </ButtonGroup>
          {isOwner && (
            <>
              <AddUrlsToQueueButton channelId={channelId} />
              <ManageShows channelId={channelId} />
            </>
          )}
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
          />
          {isOwner && (
            <SaveDefaultButton channelId={channelId} searchParams={search} />
          )}
          {viewMode === "table" && <ColumnVisibilityButton table={table} />}
        </div>
      </div>
      {viewMode === "table" ? (
        <DataTable
          columns={columns}
          data={episodesWithDetails}
          columnVisibility={columnVisibility}
          onColumnVisibilityChange={setColumnVisibility}
        />
      ) : (
        <EpisodeCards episodes={episodesWithDetails} channelId={channelId} />
      )}
    </div>
  )
}

function ChannelDetail() {
  const { channelId } = Route.useParams()

  return (
    <Suspense fallback={<PendingChannelDetails />}>
      <ChannelDetailContent channelId={channelId} />
    </Suspense>
  )
}
