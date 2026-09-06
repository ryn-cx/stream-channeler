// TODO: Validate
import { useQuery } from "@tanstack/react-query"
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
    canonical_titles: {},
    canonical_sources: {},
    groups: [],
    total: pages[0]?.total ?? 0,
  }

  for (const page of pages) {
    merged.titles?.push(...(page.titles ?? []))
    Object.assign(merged.sources ?? {}, page.sources)
    Object.assign(merged.canonical_titles ?? {}, page.canonical_titles)
    Object.assign(merged.canonical_sources ?? {}, page.canonical_sources)
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
export function useChannelTitlesPage(channelId: string, pageIndex: number) {
  return useQuery({
    queryKey: ["channel-titles", channelId, pageIndex],
    queryFn: () =>
      ChannelsService.getChannelTitles({
        channelId,
        offset: pageIndex * CHANNEL_TITLE_PAGE,
        limit: CHANNEL_TITLE_PAGE,
      }),
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
  canonicalTitleIds: string[],
) {
  return useQuery({
    queryKey: ["channel-title-stats", channelId, canonicalTitleIds],
    queryFn: () =>
      ChannelsService.getChannelTitleStats({ channelId, canonicalTitleIds }),
    enabled: canonicalTitleIds.length > 0,
  })
}
