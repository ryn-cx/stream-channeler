// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { ChannelsService } from "@/client"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface ToggleEpisodeParams {
  episodeId: string
  showId: string
}

export function useToggleEpisodeWhitelist(
  channelId: string,
  queryChannelId: string,
) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ episodeId, showId }: ToggleEpisodeParams) =>
      ChannelsService.updateChannelWhitelist({
        channelId,
        showId,
        requestBody: {
          episodes: [{ id: episodeId, marked: true }],
        },
      }),
    onMutate: async ({ episodeId }) => {
      await queryClient.cancelQueries({
        queryKey: ["episodes", queryChannelId],
      })

      // Snapshot all matching queries (key may include randomSeed as 3rd element)
      const previousEntries = queryClient.getQueriesData({
        queryKey: ["episodes", queryChannelId],
      })

      const removeEpisode = (oldData: any) => {
        if (!oldData) return oldData
        return {
          ...oldData,
          episodes: oldData.episodes.filter((ep: any) => ep.id !== episodeId),
        }
      }

      queryClient.setQueriesData(
        { queryKey: ["episodes", queryChannelId] },
        removeEpisode,
      )

      queryClient.setQueriesData(
        { queryKey: ["episodes-preview", queryChannelId] },
        removeEpisode,
      )

      return { previousEntries }
    },
    onSuccess: () => {
      showSuccessToast("Episode whitelist status toggled successfully")
    },
    onError: (error, _variables, context) => {
      for (const [queryKey, data] of context?.previousEntries ?? []) {
        queryClient.setQueryData(queryKey, data)
      }
      handleError.call(showErrorToast, error as any)
    },
  })
}
