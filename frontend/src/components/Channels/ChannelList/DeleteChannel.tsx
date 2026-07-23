// TODO: Validate
import { Trash2 } from "lucide-react"
import { useState } from "react"

import { ChannelsService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { useDeleteTableRow } from "@/components/Common/useDeleteTableRow"

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
  const mutation = useDeleteTableRow({
    mutationFn: (channelId: string) =>
      ChannelsService.deleteChannel({ channelId }),
    rowId: id,
    successMessage: "The channel was deleted successfully",
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
        onConfirm={() => mutation.mutate(id, { onSuccess: () => onSuccess() })}
      />
    </>
  )
}

export default DeleteChannel
