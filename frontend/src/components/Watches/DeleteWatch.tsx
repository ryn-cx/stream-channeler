// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { Trash2 } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"

import { EpisodesService, type WatchedEpisodesOutput } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface DeleteWatchProps {
  id: string
  onSuccess?: () => void
}

const DeleteWatch = ({ id, onSuccess = () => {} }: DeleteWatchProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const { handleSubmit } = useForm()

  const mutation = useMutation({
    mutationFn: (watchId: string) =>
      EpisodesService.deleteWatchedEpisode({ WatchId: watchId }),
    // When mutate is called:
    onMutate: async (deletedId, context) => {
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
          watches: old!.watches.filter((w) => w.id !== deletedId),
          count: old!.count - 1,
        }),
      )

      // Return a result with the snapshotted value
      return { previousWatches }
    },
    onSuccess: () => {
      showSuccessToast("The watch entry was deleted successfully")
      setIsOpen(false)
      onSuccess()
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

  const onSubmit = async () => {
    mutation.mutate(id)
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <Tooltip>
        <TooltipTrigger asChild>
          <DialogTrigger asChild>
            <Button variant="ghost" size="icon">
              <Trash2 className="size-4 text-destructive" />
            </Button>
          </DialogTrigger>
        </TooltipTrigger>
        <TooltipContent>
          <p>Delete watch</p>
        </TooltipContent>
      </Tooltip>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Delete Watch</DialogTitle>
            <DialogDescription>
              This watch entry will be permanently deleted. Are you sure? You
              will not be able to undo this action.
            </DialogDescription>
          </DialogHeader>

          <DialogFooter className="mt-4">
            <DialogClose asChild>
              <Button variant="outline" disabled={mutation.isPending}>
                Cancel
              </Button>
            </DialogClose>
            <LoadingButton
              variant="destructive"
              type="submit"
              loading={mutation.isPending}
            >
              Delete
            </LoadingButton>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default DeleteWatch
