// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { Trash2 } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"

import { type ChannelOutput, ChannelsService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface DeleteChannelProps {
  id: string
  onSuccess?: () => void
  externalOpen?: boolean
  onExternalClose?: () => void
}

const DeleteChannel = ({
  id,
  onSuccess = () => {},
  externalOpen,
  onExternalClose,
}: DeleteChannelProps) => {
  const [internalOpen, setInternalOpen] = useState(false)
  const isOpen = externalOpen ?? internalOpen
  const setIsOpen = (open: boolean) => {
    if (externalOpen !== undefined) {
      if (!open) onExternalClose?.()
    } else {
      setInternalOpen(open)
    }
  }
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const { handleSubmit } = useForm()

  const mutation = useMutation({
    mutationFn: (channelId: string) =>
      ChannelsService.deleteChannel({ channelId }),
    // When mutate is called:
    onMutate: async (_channelId, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({ queryKey: ["channels"] })

      // Snapshot the previous value
      const previousChannels = context.client.getQueryData<
        Array<ChannelOutput>
      >(["channels"])

      // Optimistically update to the new value
      context.client.setQueryData<Array<ChannelOutput>>(["channels"], (old) =>
        old!.filter((c: { id: string }) => c.id !== id),
      )

      // Return a result with the snapshotted value
      return { previousChannels }
    },
    onSuccess: () => {
      showSuccessToast("The channel was deleted successfully")
      setIsOpen(false)
      onSuccess()
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (error, _channelId, onMutateResult, context) => {
      context.client.setQueryData(
        ["channels"],
        onMutateResult?.previousChannels,
      )
      handleError.call(showErrorToast, error as any)
    },
    // Always refetch after error or success:
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({ queryKey: ["channels"] }),
  })

  const onSubmit = async () => {
    mutation.mutate(id)
  }

  return (
    <>
      {externalOpen === undefined && (
        <Button
          variant="ghost"
          size="icon"
          title="Delete channel"
          onClick={() => setIsOpen(true)}
        >
          <Trash2 className="size-4 text-destructive" />
        </Button>
      )}
      {isOpen && (
        <Dialog open={isOpen} onOpenChange={setIsOpen}>
          <DialogContent className="sm:max-w-md">
            <form onSubmit={handleSubmit(onSubmit)}>
              <DialogHeader>
                <DialogTitle>Delete Channel</DialogTitle>
                <DialogDescription>
                  This channel will be permanently deleted. Are you sure? You
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
      )}
    </>
  )
}

export default DeleteChannel
