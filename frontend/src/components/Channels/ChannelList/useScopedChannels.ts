// TODO: Validate
import { keepPreviousData, useQuery } from "@tanstack/react-query"
import type {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
} from "@tanstack/react-table"

import {
  type ChannelListOutput,
  ChannelsService,
  type RecordScope,
} from "@/client"
import {
  type MediaTableResult,
  serializeTableQuery,
} from "@/components/Common/DataTable"

// One row shape now serves every scope and viewer.
export type ChannelRow = ChannelListOutput

export interface ScopedChannelsParams {
  offset: number
  limit: number
  sortOptions: SortingState
  filterOptions: ColumnFiltersState
}

// Every scope reads through the one channels endpoint, which decides server-side
// what the viewer may see: `public` lists every public channel, `owned` needs a
// user and `all` is admin-only.
// `isAdmin` no longer picks the endpoint, but it stays in the query key because the
// same scope returns different rows per privilege — `score` and the owner of an
// anonymous channel are only populated for an owner or an admin.
// TODO: Validate
export function useScopedChannels<TData extends ChannelRow = ChannelRow>(
  scope: RecordScope,
  isAdmin: boolean,
  params: ScopedChannelsParams,
  columns: ColumnDef<TData, unknown>[],
) {
  return useQuery({
    queryKey: [
      "channels",
      scope,
      isAdmin,
      params.offset,
      params.limit,
      params.sortOptions,
      params.filterOptions,
    ],
    queryFn: async (): Promise<MediaTableResult<TData>> =>
      (await ChannelsService.getChannels({
        scope,
        offset: params.offset,
        limit: params.limit,
        ...serializeTableQuery(params, columns),
      })) as MediaTableResult<TData>,
    placeholderData: keepPreviousData,
    refetchOnWindowFocus: false,
  })
}
