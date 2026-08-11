// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Star } from "lucide-react"

import { ChannelsService } from "@/client"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { isLoggedIn } from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { cn } from "@/lib/utils"
import { handleError } from "@/utils"

const FAVORITE_IDS_KEY = ["channels", "favorite-ids"]

// The ids are fetched once and shared by every star on the page, so toggling one
// channel updates the rest without a refetch per row.
// TODO: Validate
export function useFavoriteChannelIds() {
  const loggedIn = isLoggedIn()
  const query = useQuery({
    queryKey: FAVORITE_IDS_KEY,
    queryFn: () => ChannelsService.getFavoriteChannelIds(),
    enabled: loggedIn,
    refetchOnWindowFocus: false,
  })
  return new Set(query.data ?? [])
}

// TODO: Validate
export function FavoriteChannel({ channelId }: { channelId: string }) {
  const queryClient = useQueryClient()
  const favoriteIds = useFavoriteChannelIds()
  const { showErrorToast } = useCustomToast()
  const isFavorite = favoriteIds.has(channelId)

  const mutation = useMutation({
    mutationFn: (favorite: boolean) =>
      favorite
        ? ChannelsService.favoriteChannel({ channelId })
        : ChannelsService.unfavoriteChannel({ channelId }),
    onMutate: async (favorite) => {
      await queryClient.cancelQueries({ queryKey: FAVORITE_IDS_KEY })
      const previousIds =
        queryClient.getQueryData<string[]>(FAVORITE_IDS_KEY) ?? []
      queryClient.setQueryData<string[]>(FAVORITE_IDS_KEY, (old) =>
        favorite
          ? [...(old ?? []), channelId]
          : (old ?? []).filter((id) => id !== channelId),
      )
      return { previousIds }
    },
    onError: (error, _favorite, onMutateResult) => {
      queryClient.setQueryData(FAVORITE_IDS_KEY, onMutateResult?.previousIds)
      handleError.call(showErrorToast, error as any)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: FAVORITE_IDS_KEY })
      queryClient.invalidateQueries({ queryKey: ["channels", "favorites"] })
    },
  })

  return (
    <TooltipIconButton
      label={isFavorite ? "Remove from favorites" : "Add to favorites"}
      icon={
        <Star
          className={cn(
            "size-4",
            isFavorite && "fill-yellow-400 text-yellow-400",
          )}
        />
      }
      onClick={() => mutation.mutate(!isFavorite)}
    />
  )
}
