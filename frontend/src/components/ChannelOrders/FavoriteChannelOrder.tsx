// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Star } from "lucide-react"

import { ChannelOrdersService } from "@/client"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { isLoggedIn } from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { cn } from "@/lib/utils"
import { handleError } from "@/utils"

const FAVORITE_IDS_KEY = ["channel-orders", "favorite-ids"]

// The ids are fetched once and shared by every star on the page, so toggling one
// order updates the rest without a refetch per row.
// TODO: Validate
export function useFavoriteChannelOrderIds() {
  const query = useQuery({
    queryKey: FAVORITE_IDS_KEY,
    queryFn: () => ChannelOrdersService.getFavoriteChannelOrderIds(),
    enabled: isLoggedIn(),
    refetchOnWindowFocus: false,
  })
  return new Set(query.data ?? [])
}

// TODO: Validate
export function FavoriteChannelOrder({ orderId }: { orderId: string }) {
  const queryClient = useQueryClient()
  const favoriteIds = useFavoriteChannelOrderIds()
  const { showErrorToast } = useCustomToast()
  const isFavorite = favoriteIds.has(orderId)

  const mutation = useMutation({
    mutationFn: (favorite: boolean) =>
      favorite
        ? ChannelOrdersService.favoriteChannelOrder({ channelOrderId: orderId })
        : ChannelOrdersService.unfavoriteChannelOrder({
            channelOrderId: orderId,
          }),
    onMutate: async (favorite) => {
      await queryClient.cancelQueries({ queryKey: FAVORITE_IDS_KEY })
      const previousIds =
        queryClient.getQueryData<string[]>(FAVORITE_IDS_KEY) ?? []
      queryClient.setQueryData<string[]>(FAVORITE_IDS_KEY, (old) =>
        favorite
          ? [...(old ?? []), orderId]
          : (old ?? []).filter((id) => id !== orderId),
      )
      return { previousIds }
    },
    onError: (error, _favorite, onMutateResult) => {
      queryClient.setQueryData(FAVORITE_IDS_KEY, onMutateResult?.previousIds)
      handleError.call(showErrorToast, error as any)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: FAVORITE_IDS_KEY })
      queryClient.invalidateQueries({
        queryKey: ["channel-orders", "favorites"],
      })
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
