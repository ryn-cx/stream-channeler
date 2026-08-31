// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import type { ChannelShowGroup, ChannelShowsOutput } from "@/client"
import { ChannelsService } from "@/client"

export const CHANNEL_SHOW_PAGE = 100

// TODO: Validate
function mergeChannelShowPages(
  pages: ChannelShowsOutput[],
): ChannelShowsOutput {
  const groups = new Map<string, ChannelShowGroup>()
  const merged: ChannelShowsOutput = {
    shows: [],
    filter_only_shows: pages[0]?.filter_only_shows ?? [],
    sources: {},
    canonical_shows: {},
    canonical_sources: {},
    groups: [],
    total: pages[0]?.total ?? 0,
  }

  for (const page of pages) {
    merged.shows?.push(...(page.shows ?? []))
    Object.assign(merged.sources ?? {}, page.sources)
    Object.assign(merged.canonical_shows ?? {}, page.canonical_shows)
    Object.assign(merged.canonical_sources ?? {}, page.canonical_sources)
    for (const group of page.groups ?? []) {
      const merging = groups.get(group.channel_id)
      if (merging) {
        merging.shows?.push(...(group.shows ?? []))
      } else {
        groups.set(group.channel_id, {
          ...group,
          shows: [...(group.shows ?? [])],
        })
      }
    }
  }

  merged.groups = [...groups.values()]
  return merged
}

// TODO: Validate
export function useChannelShowsPage(channelId: string, pageIndex: number) {
  return useQuery({
    queryKey: ["channel-shows", channelId, pageIndex],
    queryFn: () =>
      ChannelsService.getChannelShows({
        channelId,
        offset: pageIndex * CHANNEL_SHOW_PAGE,
        limit: CHANNEL_SHOW_PAGE,
      }),
  })
}

// TODO: Validate
export function useAllChannelShows(
  channelId: string,
  options?: { enabled?: boolean; refetchOnWindowFocus?: boolean },
) {
  return useQuery({
    queryKey: ["channel-shows", channelId, "all"],
    queryFn: async () => {
      const pages: ChannelShowsOutput[] = []
      let offset = 0
      let total = 0
      do {
        const page = await ChannelsService.getChannelShows({
          channelId,
          offset,
          limit: CHANNEL_SHOW_PAGE,
        })
        pages.push(page)
        total = page.total ?? 0
        offset += CHANNEL_SHOW_PAGE
      } while (offset < total)
      return mergeChannelShowPages(pages)
    },
    enabled: options?.enabled,
    refetchOnWindowFocus: options?.refetchOnWindowFocus,
  })
}

// TODO: Validate
export function useChannelShowStats(
  channelId: string,
  canonicalShowIds: string[],
) {
  return useQuery({
    queryKey: ["channel-show-stats", channelId, canonicalShowIds],
    queryFn: () =>
      ChannelsService.getChannelShowStats({ channelId, canonicalShowIds }),
    enabled: canonicalShowIds.length > 0,
  })
}
