// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { Check } from "lucide-react"

import {
  type WatchesListOutput,
  WatchesService,
  type WatchOutput,
} from "@/client"
import { Button } from "@/components/ui/button"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface VerifyWatchProps {
  id: string
  verified: boolean
}

export default function VerifyWatch({ id, verified }: VerifyWatchProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const verifyMutation = useMutation({
    mutationFn: () =>
      WatchesService.updateWatch({
        watchId: id,
        requestBody: { verified: true },
      }),
    // When mutate is called:
    onMutate: async (_variables, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({ queryKey: ["watches"] })

      // Snapshot the previous value
      const previousWatches = context.client.getQueryData<WatchesListOutput>([
        "watches",
      ])

      // Optimistically update to the new value
      context.client.setQueryData<WatchesListOutput>(["watches"], (old) => {
        if (!old) return old
        const verifiedWatch = old.watches.find((w) => w.id === id)
        if (!verifiedWatch) return old
        const verifiedEpisode = old.episodes[verifiedWatch.episode_id]
        const verifiedSeason = old.seasons[verifiedEpisode.season_id]
        const verifiedShow = old.shows[verifiedSeason.show_id]
        const verifiedSource = old.sources[verifiedShow.source_id]
        return {
          ...old,
          watches: old.watches.map((w) => {
            if (w.watch_date !== verifiedWatch.watch_date) return w
            const episode = old.episodes[w.episode_id]
            if (episode.key !== verifiedEpisode.key) return w
            const season = old.seasons[episode.season_id]
            const show = old.shows[season.show_id]
            const source = old.sources[show.source_id]
            if (source.plugin_id !== verifiedSource.plugin_id) return w
            return { ...w, verified: true, pending: true }
          }),
        }
      })

      // Return a result with the snapshotted value
      return { previousWatches }
    },
    onSuccess: (result: WatchOutput[]) => {
      const message =
        result.length > 1
          ? `${result.length} watches verified successfully`
          : "Watch verified successfully"
      showSuccessToast(message)
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (error, _variables, onMutateResult, context) => {
      context.client.setQueryData(["watches"], onMutateResult?.previousWatches)
      handleError.call(showErrorToast, error as any)
    },
    // Always refetch after error or success:
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({ queryKey: ["watches"] }),
  })

  if (verified) {
    return null
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => verifyMutation.mutate()}
          disabled={verifyMutation.isPending}
        >
          <Check className="size-4" />
        </Button>
      </TooltipTrigger>
      <TooltipContent>
        <p>Verify watch</p>
      </TooltipContent>
    </Tooltip>
  )
}
