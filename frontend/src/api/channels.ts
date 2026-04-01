import {
  type ChannelsGetChannelEpisodesData,
  type ChannelsGetChannelEpisodesResponse,
  ChannelsService,
} from "@/client"
import type { CancelablePromise } from "@/client/core/CancelablePromise"

/**
 * Wrapper around ChannelsService.getChannelEpisodes that JSON-stringifies
 * sortBy entries. The generated SDK serializes objects in query params with
 * bracket notation (sort_by[model]=episode) which FastAPI cannot parse.
 * Stringifying each entry produces sort_by={"model":"episode",...} which the
 * backend's parse_sort_key_input handles via json.loads.
 */
export function getChannelEpisodes(
  data: ChannelsGetChannelEpisodesData,
): CancelablePromise<ChannelsGetChannelEpisodesResponse> {
  return ChannelsService.getChannelEpisodes({
    ...data,
    sortBy: data.sortBy?.map((entry) => JSON.stringify(entry)) as any,
  })
}
