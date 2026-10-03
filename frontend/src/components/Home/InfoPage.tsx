// TODO: Validate
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { useEffect, useMemo } from "react"

import {
  ChannelsService,
  type HomeGuideOutput,
  VideoStoreService,
} from "@/client"
import type { EpisodeWithDetails } from "@/components/Channels/ChannelDetail/columns"
import { ChannelGuide } from "@/components/Channels/ChannelGuide/ChannelGuide"
import type { BrowseChannel } from "@/components/Channels/ChannelList/ChannelsBrowse"
import { prefetchScopedChannels } from "@/components/Channels/ChannelList/useScopedChannels"
import {
  readStoredBrowsePageSize,
  useBrowsePagination,
} from "@/components/Common/BrowsePagination"
import { Skeleton } from "@/components/ui/skeleton"
import useAuth from "@/hooks/useAuth"

// TODO: Validate
function homeGuideRows(guide: HomeGuideOutput) {
  const rows: BrowseChannel[] = []
  const preloadedEpisodes: Record<string, EpisodeWithDetails[]> = {}
  for (const channel of guide.channels) {
    rows.push({
      id: channel.id,
      name: channel.name,
      default_order: channel.default_order,
    } as BrowseChannel)
    preloadedEpisodes[channel.id] = channel.episode_ids.map((episodeId) => {
      const episode = guide.episodes[episodeId]
      const season = guide.seasons[episode.season_id]
      const title = guide.titles[season.title_id]
      const source = guide.sources[title.source_id]
      return {
        ...episode,
        id: episodeId,
        channel_id: channel.id,
        channel_ids: channel.member_channel_ids[episodeId] ?? [channel.id],
        season,
        title: { ...title, id: season.title_id },
        source,
        plugin: guide.plugins[source.plugin_id],
      } as EpisodeWithDetails
    })
  }
  return { rows, preloadedEpisodes }
}

// TODO: Validate
export function InfoPage() {
  const { user } = useAuth()
  const [pagination, setPagination] = useBrowsePagination(
    "home-guide-page-size",
  )
  const query = useQuery({
    queryKey: ["home-guide"],
    queryFn: () => ChannelsService.getHomeGuide(),
    staleTime: Number.POSITIVE_INFINITY,
    refetchOnWindowFocus: false,
  })
  const queryClient = useQueryClient()
  const isAdmin = user?.is_superuser ?? false
  const homeGuideLoaded = query.data !== undefined
  const guide = useMemo(
    () => (query.data ? homeGuideRows(query.data) : undefined),
    [query.data],
  )

  useEffect(() => {
    if (!homeGuideLoaded) return
    prefetchScopedChannels(
      queryClient,
      "public",
      isAdmin,
      {
        offset: 0,
        limit: readStoredBrowsePageSize("channels-public-browse-page-size"),
        sortOptions: [],
        filterOptions: [],
      },
      [],
      true,
    )
  }, [homeGuideLoaded, queryClient, isAdmin])

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      {/* Hero Section */}
      <div className="container mx-auto px-4 pt-4 pb-8">
        <div className="text-center max-w-4xl mx-auto">
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight mb-6">
            Turn Streaming Services Into
            <span className="text-primary block">Personalized TV Channels</span>
          </h1>
          <div className="grid gap-8 text-lg text-muted-foreground md:grid-cols-2 md:text-left">
            <div className="space-y-2">
              <SectionHeading targetId="home-channels">Channels</SectionHeading>
              <p>
                Here are the most popular channels on the site.{" "}
                {user ? (
                  <>
                    Want to make your own channels with your favorite media?{" "}
                    <Link
                      to="/dashboard"
                      className="text-primary hover:underline"
                    >
                      Head to your dashboard
                    </Link>
                    .
                  </>
                ) : (
                  <>
                    Want to make your own channels with your favorite media?{" "}
                    <Link to="/signup" className="text-primary hover:underline">
                      Create an account
                    </Link>
                    .
                  </>
                )}
              </p>
              <BrowseAllChannels totalCount={query.data?.total_count} />
            </div>
            <div className="space-y-2">
              <SectionHeading targetId="home-video-store">
                Video Store
              </SectionHeading>
              <p>
                Browse everything a streaming service has to offer, laid out on
                the shelves of an old school movie rental store. Pick up the
                cases and build a collection of your favorites before watching
                them.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div id="home-channels" className="scroll-mt-4">
        {guide ? (
          <ChannelGuide
            rows={guide.rows}
            preloadedEpisodes={guide.preloadedEpisodes}
            isServer
            serverRowCount={guide.rows.length}
            pagination={pagination}
            onPaginationChange={setPagination}
            showChannelNumber={false}
            hideEmptyChannels
            showPagination={false}
          />
        ) : (
          <div className="px-[4%] pb-8">
            <Skeleton className="h-96 w-full rounded-md" />
          </div>
        )}
      </div>

      <div className="container mx-auto px-4 pt-4 pb-12 text-center text-xl text-muted-foreground">
        <BrowseAllChannels totalCount={query.data?.total_count} />
      </div>

      <div className="container mx-auto px-4">
        <hr className="border-t-2 border-border" />
      </div>

      <VideoStorePreview />
    </div>
  )
}

// TODO: Validate
function SectionHeading({
  targetId,
  children,
}: {
  targetId: string
  children: React.ReactNode
}) {
  return (
    <h2 className="text-2xl font-semibold text-foreground">
      <button
        type="button"
        className="cursor-pointer text-primary underline-offset-4 hover:underline"
        onClick={() =>
          document
            .getElementById(targetId)
            ?.scrollIntoView({ behavior: "smooth", block: "start" })
        }
      >
        {children}
      </button>
    </h2>
  )
}

// TODO: Validate
function BrowseAllChannels({ totalCount }: { totalCount?: number }) {
  return (
    <p>
      Don't see a channel you like?{" "}
      <Link to="/channels/browse" className="text-primary hover:underline">
        {totalCount === undefined
          ? "Browse all of the channels"
          : `Browse all ${totalCount.toLocaleString()} channels`}
      </Link>
      .
    </p>
  )
}

// TODO: Validate
function VideoStorePreview() {
  const { data: sources } = useQuery({
    queryKey: ["video-store-sources"],
    queryFn: () => VideoStoreService.getStoreSources(),
    refetchOnWindowFocus: false,
  })
  const netflix = sources?.find((source) => source.plugin_name === "Netflix")

  return (
    <div
      id="home-video-store"
      className="container mx-auto max-w-4xl scroll-mt-4 px-4 pt-12 pb-16 text-center text-xl text-muted-foreground"
    >
      <h2 className="mb-6 text-3xl font-bold tracking-tight text-foreground md:text-5xl">
        Browse Streaming Services Like
        <span className="block text-primary">An Old School Video Store</span>
      </h2>
      <img
        src="/video-store.webp"
        alt="Shelves of cases inside the 3D video store"
        className="w-full rounded-lg border"
      />
      <div className="mt-6 space-y-2">
        {netflix && (
          <p>
            Want to try it out?{" "}
            <Link
              to="/video-store/sources/$sourceId"
              params={{ sourceId: netflix.id }}
              className="text-primary hover:underline"
            >
              Walk through the Netflix store
            </Link>
            .
          </p>
        )}
        <p>
          Looking for a different service?{" "}
          <Link to="/video-store" className="text-primary hover:underline">
            {sources === undefined
              ? "Browse all of the stores"
              : `Browse all ${sources.length.toLocaleString()} stores`}
          </Link>
          .
        </p>
      </div>
    </div>
  )
}
