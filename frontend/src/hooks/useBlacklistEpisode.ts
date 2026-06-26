// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { ChannelsService } from "@/client"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface BlacklistEpisodeParams {
  targetChannelId: string
  showId: string
  episodeId: string
  expiresAt: string | null
}

// Blacklists a single episode on a chosen channel (a base channel the episode belongs
// to, or the channel currently being viewed). `currentChannelId` is only used to
// optimistically drop the episode from the channel page the user is looking at.
export function useBlacklistEpisode(currentChannelId: string) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      targetChannelId,
      showId,
      episodeId,
      expiresAt,
    }: BlacklistEpisodeParams) =>
      ChannelsService.blacklistChannelEpisode({
        channelId: targetChannelId,
        requestBody: {
          show_id: showId,
          episode_id: episodeId,
          expires_at: expiresAt,
        },
      }),
    onMutate: async ({ episodeId }) => {
      await queryClient.cancelQueries({
        queryKey: ["episodes", currentChannelId],
      })

      const previousEntries = queryClient.getQueriesData({
        queryKey: ["episodes", currentChannelId],
      })

      const removeEpisode = (oldData: any) => {
        if (!oldData) return oldData
        return {
          ...oldData,
          episodes: oldData.episodes.filter((ep: any) => ep.id !== episodeId),
        }
      }

      queryClient.setQueriesData(
        { queryKey: ["episodes", currentChannelId] },
        removeEpisode,
      )
      queryClient.setQueriesData(
        { queryKey: ["episodes-preview", currentChannelId] },
        removeEpisode,
      )

      return { previousEntries }
    },
    onSuccess: () => {
      showSuccessToast("Episode blacklisted successfully")
    },
    onError: (error, _variables, context) => {
      for (const [queryKey, data] of context?.previousEntries ?? []) {
        queryClient.setQueryData(queryKey, data)
      }
      handleError.call(showErrorToast, error as any)
    },
  })
}
