// TODO: Validate
import {
  keepPreviousData,
  type QueryClient,
  queryOptions,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query"
import type {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
} from "@tanstack/react-table"
import { useEffect, useEffectEvent } from "react"

import {
  type ChannelListOutput,
  ChannelsService,
  type RecordScope,
} from "@/client"
import { prefetchChannelEpisodePreviews } from "@/components/Channels/ChannelList/useChannelEpisodePreview"
import {
  type MediaTableResult,
  serializeTableQuery,
} from "@/components/Common/DataTable"
import { getSeedForThisLoad } from "@/randomSeed"

const LIST_RANDOM_SEED = getSeedForThisLoad("channel-list")

// One row shape now serves every scope and viewer.
export type ChannelRow = ChannelListOutput

export interface ScopedChannelsParams {
  offset: number
  limit: number
  sortOptions: SortingState
  filterOptions: ColumnFiltersState
  titleId?: string
}

// Every scope reads through the one channels endpoint, which decides server-side
// what the viewer may see: `public` lists every public channel, `owned` needs a
// user and `all` is admin-only.
// `isAdmin` no longer picks the endpoint, but it stays in the query key because the
// same scope returns different rows per privilege — `score` and the owner of an
// anonymous channel are only populated for an owner or an admin.
// TODO: Validate
function scopedChannelsQueryOptions<TData extends ChannelRow = ChannelRow>(
  scope: RecordScope,
  isAdmin: boolean,
  params: ScopedChannelsParams,
  columns: ColumnDef<TData, unknown>[],
) {
  return queryOptions({
    queryKey: [
      "channels",
      scope,
      isAdmin,
      params.offset,
      params.limit,
      params.sortOptions,
      params.filterOptions,
      params.titleId,
      LIST_RANDOM_SEED,
    ],
    queryFn: async (): Promise<MediaTableResult<TData>> =>
      (await ChannelsService.getChannels({
        scope,
        offset: params.offset,
        limit: params.limit,
        titleId: params.titleId,
        randomSeed: LIST_RANDOM_SEED,
        ...serializeTableQuery(params, columns),
      })) as MediaTableResult<TData>,
    staleTime: 60 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
    refetchOnWindowFocus: false,
  })
}

// TODO: Validate
export function useScopedChannels<TData extends ChannelRow = ChannelRow>(
  scope: RecordScope,
  isAdmin: boolean,
  params: ScopedChannelsParams,
  columns: ColumnDef<TData, unknown>[],
) {
  return useQuery({
    ...scopedChannelsQueryOptions(scope, isAdmin, params, columns),
    placeholderData: keepPreviousData,
  })
}

// TODO: Validate
export async function prefetchScopedChannels<
  TData extends ChannelRow = ChannelRow,
>(
  queryClient: QueryClient,
  scope: RecordScope,
  isAdmin: boolean,
  params: ScopedChannelsParams,
  columns: ColumnDef<TData, unknown>[],
  withEpisodes: boolean,
) {
  const options = scopedChannelsQueryOptions(scope, isAdmin, params, columns)
  await queryClient.prefetchQuery(options)
  const page = queryClient.getQueryData(options.queryKey)
  if (page && withEpisodes) {
    prefetchChannelEpisodePreviews(queryClient, page.data)
  }
}

// TODO: Validate
export function usePrefetchNeighborChannelPages<
  TData extends ChannelRow = ChannelRow,
>(
  page: MediaTableResult<TData> | undefined,
  scope: RecordScope,
  isAdmin: boolean,
  params: ScopedChannelsParams,
  columns: ColumnDef<TData, unknown>[],
  withEpisodes: boolean,
) {
  const queryClient = useQueryClient()
  const prefetchNeighbors = useEffectEvent(
    (filteredCount: number, includeEpisodes: boolean) => {
      for (const offset of [
        params.offset + params.limit,
        params.offset - params.limit,
      ]) {
        if (offset >= 0 && offset < filteredCount) {
          prefetchScopedChannels(
            queryClient,
            scope,
            isAdmin,
            { ...params, offset },
            columns,
            includeEpisodes,
          )
        }
      }
    },
  )
  useEffect(() => {
    if (page?.is_server_side) {
      prefetchNeighbors(page.filtered_count, withEpisodes)
    }
  }, [page, withEpisodes])
}
