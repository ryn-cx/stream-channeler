// TODO: Validate
import {
  type ChannelsGetChannelEpisodesData,
  type ChannelsGetChannelEpisodesResponse,
  ChannelsService,
} from "@/client"
import type { CancelablePromise } from "@/client/core/CancelablePromise"

export function getChannelEpisodes(
  data: ChannelsGetChannelEpisodesData,
): CancelablePromise<ChannelsGetChannelEpisodesResponse> {
  return ChannelsService.getChannelEpisodes({
    ...data,
    sortBy: data.sortBy?.map((entry) => JSON.stringify(entry)) as any,
  })
}
