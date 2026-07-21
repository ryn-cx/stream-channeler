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
        return {
          ...old,
          watches: old.watches.map((w) =>
            w.id === id ? { ...w, verified: true, pending: true } : w,
          ),
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
