// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { Check } from "lucide-react"

import { MediaService, type WatchedEpisodesOutput } from "@/client"
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
  watch_date: string
}

export default function VerifyWatch({
  id,
  verified,
  watch_date,
}: VerifyWatchProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const verifyMutation = useMutation({
    mutationFn: () =>
      MediaService.patchWatchedEpisode({
        episodeWatchId: id,
        requestBody: {
          watch_date: watch_date,
          verified: true,
        },
      }),
    // When mutate is called:
    onMutate: async (_variables, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({ queryKey: ["watches"] })

      // Snapshot the previous value
      const previousWatches =
        context.client.getQueryData<WatchedEpisodesOutput>(["watches"])

      // Optimistically update to the new value
      context.client.setQueryData<WatchedEpisodesOutput>(
        ["watches"],
        (old) => ({
          ...old!,
          watches: old!.watches.map((w) =>
            w.id === id ? { ...w, verified: true } : w,
          ),
        }),
      )

      // Return a result with the snapshotted value
      return { previousWatches }
    },
    onSuccess: () => {
      showSuccessToast("Watch verified successfully")
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
