// TODO: Validate
import { keepPreviousData, useQuery } from "@tanstack/react-query"
import type { ChannelTitleGroup, ChannelTitlesOutput } from "@/client"
import { ChannelsService } from "@/client"

export const CHANNEL_TITLE_PAGE = 100

// TODO: Validate
function mergeChannelTitlePages(
  pages: ChannelTitlesOutput[],
): ChannelTitlesOutput {
  const groups = new Map<string, ChannelTitleGroup>()
  const merged: ChannelTitlesOutput = {
    titles: [],
    filter_only_titles: pages[0]?.filter_only_titles ?? [],
    sources: {},
    tmdb_titles: {},
    tmdb_sources: {},
    groups: [],
    total: pages[0]?.total ?? 0,
  }

  for (const page of pages) {
    merged.titles?.push(...(page.titles ?? []))
    Object.assign(merged.sources ?? {}, page.sources)
    Object.assign(merged.tmdb_titles ?? {}, page.tmdb_titles)
    Object.assign(merged.tmdb_sources ?? {}, page.tmdb_sources)
    for (const group of page.groups ?? []) {
      const merging = groups.get(group.channel_id)
      if (merging) {
        merging.titles?.push(...(group.titles ?? []))
      } else {
        groups.set(group.channel_id, {
          ...group,
          titles: [...(group.titles ?? [])],
        })
      }
    }
  }

  merged.groups = [...groups.values()]
  return merged
}

// TODO: Validate
export function channelTitlesQueryKey(
  channelId: string,
  pageIndex: number,
  query: string,
) {
  return ["channel-titles", channelId, pageIndex, query]
}

// TODO: Validate
export function useChannelTitlesPage(
  channelId: string,
  pageIndex: number,
  query = "",
) {
  return useQuery({
    queryKey: channelTitlesQueryKey(channelId, pageIndex, query),
    queryFn: () =>
      ChannelsService.getChannelTitles({
        channelId,
        offset: pageIndex * CHANNEL_TITLE_PAGE,
        limit: CHANNEL_TITLE_PAGE,
        query: query || undefined,
      }),
    // The page a listing is on is read from the total it comes back with, so a
    // page being fetched must not read as a listing of nothing.
    placeholderData: keepPreviousData,
  })
}

// TODO: Validate
export function useAllChannelTitles(
  channelId: string,
  options?: { enabled?: boolean; refetchOnWindowFocus?: boolean },
) {
  return useQuery({
    queryKey: ["channel-titles", channelId, "all"],
    queryFn: async () => {
      const pages: ChannelTitlesOutput[] = []
      let offset = 0
      let total = 0
      do {
        const page = await ChannelsService.getChannelTitles({
          channelId,
          offset,
          limit: CHANNEL_TITLE_PAGE,
        })
        pages.push(page)
        total = page.total ?? 0
        offset += CHANNEL_TITLE_PAGE
      } while (offset < total)
      return mergeChannelTitlePages(pages)
    },
    enabled: options?.enabled,
    refetchOnWindowFocus: options?.refetchOnWindowFocus,
  })
}

// TODO: Validate
export function useChannelTitleStats(
  channelId: string,
  tmdbTitleIds: string[],
) {
  return useQuery({
    queryKey: ["channel-title-stats", channelId, tmdbTitleIds],
    queryFn: () =>
      ChannelsService.getChannelTitleStats({ channelId, tmdbTitleIds }),
    enabled: tmdbTitleIds.length > 0,
  })
}
