// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { Check } from "lucide-react"

import { type WatchesListOutput, WatchesService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface CompleteWatchProps {
  id: string
  completed: boolean
}

// TODO: Validate
export default function CompleteWatch({ id, completed }: CompleteWatchProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const completeMutation = useMutation({
    mutationFn: () =>
      WatchesService.updateWatch({
        watchId: id,
        requestBody: { completed: true },
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
        return {
          ...old,
          watches: old.watches.map((w) =>
            w.id === id ? { ...w, completed: true, pending: true } : w,
          ),
        }
      })

      // Return a result with the snapshotted value
      return { previousWatches }
    },
    onSuccess: () => {
      showSuccessToast("Watch completed successfully")
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

  if (completed) {
    return null
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => completeMutation.mutate()}
          disabled={completeMutation.isPending}
        >
          <Check className="size-4" />
        </Button>
      </TooltipTrigger>
      <TooltipContent>
        <p>Complete watch</p>
      </TooltipContent>
    </Tooltip>
  )
}
