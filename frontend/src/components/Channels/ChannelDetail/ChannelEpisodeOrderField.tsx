// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { ChannelsService } from "@/client"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

export const TMDB_OWN_ORDER = "__own__"

interface ChannelEpisodeOrderFieldProps {
  channelId: string
  tmdbTitleId: string
}

// TODO: Validate
export function ChannelEpisodeOrderField({
  channelId,
  tmdbTitleId,
}: ChannelEpisodeOrderFieldProps) {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ["channelTitleEpisodeOrder", channelId, tmdbTitleId],
    queryFn: () =>
      ChannelsService.getChannelEpisodeOrder({ channelId, tmdbTitleId }),
  })

  const mutation = useMutation({
    mutationFn: (orderId: string) =>
      ChannelsService.updateChannelEpisodeOrder({
        channelId,
        tmdbTitleId,
        requestBody: {
          tmdb_episode_order_id: orderId === TMDB_OWN_ORDER ? null : orderId,
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["channelTitleEpisodeOrder", channelId, tmdbTitleId],
      })
      queryClient.invalidateQueries({ queryKey: ["episodes", channelId] })
      queryClient.invalidateQueries({
        queryKey: ["episodes-preview", channelId],
      })
    },
  })

  const options = data?.orders ?? []
  const value = data?.tmdb_episode_order_id ?? TMDB_OWN_ORDER

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 p-4 border rounded-md bg-muted/50 shrink-0">
      <div className="min-w-0">
        <h3 className="font-semibold">Episode order</h3>
        {isLoading && (
          <p className="text-sm text-muted-foreground mt-1">
            Reading the orders TMDB holds…
          </p>
        )}
        {!isLoading && options.length === 0 && (
          <p className="text-sm text-muted-foreground mt-1">
            TMDB holds no other order for this title.
          </p>
        )}
      </div>
      <Select
        value={value}
        onValueChange={(orderId) => mutation.mutate(orderId)}
        disabled={isLoading || mutation.isPending}
      >
        <SelectTrigger className="w-72 shrink-0">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={TMDB_OWN_ORDER}>
            TMDB's own order (aired)
          </SelectItem>
          {options.map((order) => (
            <SelectItem key={order.id} value={order.id}>
              {order.name} — {order.group_count} seasons, {order.episode_count}{" "}
              episodes
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
