// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { Trash2 } from "lucide-react"
import { useState } from "react"

import { ChannelsService } from "@/client"
import type { ChannelTableData } from "@/components/Channels/ChannelList/columns"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
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
        Array<ChannelTableData>
      >(["channels"])

      // Optimistically mark as pending
      context.client.setQueryData<Array<ChannelTableData>>(
        ["channels"],
        (old) => old!.map((c) => (c.id === id ? { ...c, pending: true } : c)),
      )

      // Return a result with the snapshotted value
      return { previousChannels }
    },
    onSuccess: (_data, _channelId, _onMutateResult, context) => {
      showSuccessToast("The channel was deleted successfully")
      onSuccess()
      context.client.setQueryData<Array<ChannelTableData>>(
        ["channels"],
        (old) => old?.filter((c) => c.id !== id),
      )
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

  return (
    <>
      {externalOpen === undefined && (
        <TooltipIconButton
          label="Delete Channel"
          icon={<Trash2 />}
          className="text-destructive hover:text-destructive"
          onClick={() => setIsOpen(true)}
        />
      )}
      <ConfirmDialog
        open={isOpen}
        onOpenChange={setIsOpen}
        title="Delete Channel"
        description="This channel will be permanently deleted. Are you sure? You will not be able to undo this action."
        confirmLabel="Delete"
        onConfirm={() => mutation.mutate(id)}
      />
    </>
  )
}

export default DeleteChannel
