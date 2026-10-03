// TODO: Validate
import {
  type QueryClient,
  queryOptions,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query"
import type { PaginationState } from "@tanstack/react-table"
import { useEffect, useMemo } from "react"

import { getChannelEpisodes } from "@/api/channels"
import type { ChannelEpisodesOutput, ChannelOutput } from "@/client"
import type { EpisodeWithDetails } from "@/components/Channels/ChannelDetail/columns"
import type { BrowseChannel } from "@/components/Channels/ChannelList/ChannelsBrowse"
import { writeChannelDetails } from "@/components/Channels/ChannelList/episodePreviewCache"
import { getSeedForThisLoad } from "@/randomSeed"

// TODO: Validate
export function parseDefaultOrder(channel: BrowseChannel) {
  return channel.default_order
    ? (() => {
        try {
          return JSON.parse(channel.default_order)
        } catch {
          return {}
        }
      })()
    : {}
}

// TODO: Validate
export function channelEpisodesWithDetails(
  data: ChannelEpisodesOutput | undefined,
): EpisodeWithDetails[] {
  return (data?.episodes ?? []).map((episode) => {
    const season = data!.seasons[episode.season_id]
    const title = data!.titles[season.title_id]
    const source = data!.sources[title.source_id]
    const plugin = data!.plugins[source.plugin_id]
    return { ...episode, season, title, source, plugin }
  })
}

// TODO: Validate
function channelEpisodePreviewQueryOptions(channel: BrowseChannel) {
  const defaultOrder = parseDefaultOrder(channel)
  const randomSeed = getSeedForThisLoad(channel.id)
  return queryOptions({
    queryKey: ["episodes-preview", channel.id, defaultOrder, randomSeed],
    queryFn: async () => {
      return await getChannelEpisodes({
        channelId: channel.id,
        limit: 20,
        randomSeed,
        ...defaultOrder,
      })
    },
    staleTime: 60 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
    refetchOnWindowFocus: false,
    retry: false,
  })
}

// TODO: Validate
export function prefetchChannelEpisodePreviews(
  queryClient: QueryClient,
  channels: BrowseChannel[],
) {
  for (const channel of channels) {
    queryClient.prefetchQuery(channelEpisodePreviewQueryOptions(channel))
  }
}

// TODO: Validate
export function usePrefetchNeighborPageEpisodes(
  rows: BrowseChannel[],
  pagination: PaginationState,
  enabled: boolean,
) {
  const queryClient = useQueryClient()
  const { pageIndex, pageSize } = pagination
  useEffect(() => {
    if (!enabled) return
    const pageStart = pageIndex * pageSize
    prefetchChannelEpisodePreviews(queryClient, [
      ...rows.slice(pageStart + pageSize, pageStart + 2 * pageSize),
      ...rows.slice(Math.max(0, pageStart - pageSize), pageStart),
    ])
  }, [queryClient, rows, pageIndex, pageSize, enabled])
}

// TODO: Validate
export function useChannelEpisodePreview(channel: BrowseChannel) {
  const defaultOrder = parseDefaultOrder(channel)

  const hasDefaultOrder = Object.keys(defaultOrder).length > 0

  const randomSeed = useMemo(() => getSeedForThisLoad(channel.id), [channel.id])

  useEffect(() => {
    writeChannelDetails(channel as ChannelOutput)
  }, [channel])

  const orderedQuery = useQuery(channelEpisodePreviewQueryOptions(channel))

  // A saved default order can be rejected by the API when it was stored under an
  // older schema, so retry without any options rather than losing the whole row.
  const orderRejected = orderedQuery.isError && hasDefaultOrder
  const fallbackQuery = useQuery({
    queryKey: ["episodes-preview", channel.id, "no-options", randomSeed],
    queryFn: async () => {
      return await getChannelEpisodes({
        channelId: channel.id,
        limit: 10,
        randomSeed,
      })
    },
    enabled: orderRejected,
    staleTime: 60 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
    refetchOnWindowFocus: false,
    retry: false,
  })

  const query = orderRejected ? fallbackQuery : orderedQuery
  const data = query.data

  const episodes = channelEpisodesWithDetails(data)

  return {
    defaultOrder,
    episodes,
    isLoading:
      orderedQuery.isPending || (orderRejected && fallbackQuery.isPending),
    isRefreshing: query.isFetching && data !== undefined,
    loadFailed: orderRejected ? fallbackQuery.isError : orderedQuery.isError,
    orderRejected,
  }
}
