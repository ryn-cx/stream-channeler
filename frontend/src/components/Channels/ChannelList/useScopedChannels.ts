// TODO: Validate
import { keepPreviousData, useQuery } from "@tanstack/react-query"
import type {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
} from "@tanstack/react-table"

import {
  type AdminScope,
  type ChannelAdminOutput,
  type ChannelOutput,
  type ChannelPublicOutput,
  ChannelsService,
} from "@/client"
import {
  type MediaTableResult,
  serializeTableQuery,
} from "@/components/Common/DataTable"

export type ChannelRow =
  | ChannelOutput
  | ChannelPublicOutput
  | ChannelAdminOutput

export interface ScopedChannelsParams {
  offset: number
  limit: number
  sortOptions: SortingState
  filterOptions: ColumnFiltersState
}

// Admins read every tab through the admin endpoint, the only one that carries
// `score` and that can serve all three scopes; everyone else uses the owned and
// public endpoints.
// TData is whichever row shape the scope/isAdmin pair actually returns, which the
// caller pins through its columns: admins always get `ChannelAdminOutput`, while
// a regular user gets `ChannelPublicOutput` on the public tab.
export function useScopedChannels<TData extends ChannelRow = ChannelRow>(
  scope: AdminScope,
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
    queryFn: async (): Promise<MediaTableResult<TData>> => {
      if (isAdmin) {
        return (await ChannelsService.adminGetChannels({
          scope,
          offset: params.offset,
          limit: params.limit,
          ...serializeTableQuery(params, columns),
        })) as MediaTableResult<TData>
      }
      if (scope === "public") {
        // The public endpoint always pages server-side, ordered by score.
        const page = await ChannelsService.getPublicChannels({
          offset: params.offset,
          limit: params.limit,
        })
        return {
          data: page.data,
          total_count: page.count,
          filtered_count: page.count,
          is_server_side: true,
        } as MediaTableResult<TData>
      }
      // The owned endpoint returns a plain list, so give it the shape the table
      // expects and let the client handle sorting, filtering and paging.
      const channels = await ChannelsService.getChannels()
      return {
        data: channels,
        total_count: channels.length,
        filtered_count: channels.length,
        is_server_side: false,
      } as MediaTableResult<TData>
    },
    placeholderData: keepPreviousData,
    refetchOnWindowFocus: false,
  })
}
