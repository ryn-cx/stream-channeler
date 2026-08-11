// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { Trash2 } from "lucide-react"
import { useState } from "react"

import { type Message, type WatchesListOutput, WatchesService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface DeleteWatchProps {
  id: string
  onSuccess?: () => void
}

// TODO: Validate
const DeleteWatch = ({ id, onSuccess = () => {} }: DeleteWatchProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: (watchId: string) => WatchesService.deleteWatch({ watchId }),
    // When mutate is called:
    onMutate: async (deletedId, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({ queryKey: ["watches"] })

      // Snapshot the previous value
      const previousWatches = context.client.getQueryData<WatchesListOutput>([
        "watches",
      ])

      // Optimistically mark the watch as pending.
      context.client.setQueryData<WatchesListOutput>(["watches"], (old) => {
        if (!old) return old
        return {
          ...old,
          watches: old.watches.map((watch) =>
            watch.id === deletedId
              ? ({ ...watch, pending: true } as typeof watch)
              : watch,
          ),
        }
      })

      // Return a result with the snapshotted value
      return { previousWatches }
    },
    onSuccess: (result: Message, deletedId, _onMutateResult, context) => {
      showSuccessToast(result.message)
      onSuccess()
      context.client.setQueryData<WatchesListOutput>(["watches"], (old) => {
        if (!old) return old
        return {
          ...old,
          watches: old.watches.filter((watch) => watch.id !== deletedId),
        }
      })
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (error, _deletedId, onMutateResult, context) => {
      context.client.setQueryData(["watches"], onMutateResult?.previousWatches)
      handleError.call(showErrorToast, error as any)
    },
    // Always refetch after error or success:
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({ queryKey: ["watches"] }),
  })

  return (
    <>
      <TooltipIconButton
        label="Delete Watch"
        icon={<Trash2 />}
        className="text-destructive hover:text-destructive"
        onClick={() => setIsOpen(true)}
      />
      <ConfirmDialog
        open={isOpen}
        onOpenChange={setIsOpen}
        title="Delete Watch"
        description="This watch entry will be permanently deleted. Are you sure? You will not be able to undo this action."
        confirmLabel="Delete"
        onConfirm={() => mutation.mutate(id)}
      />
    </>
  )
}

export default DeleteWatch
