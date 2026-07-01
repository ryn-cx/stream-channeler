// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { Trash2 } from "lucide-react"
import { useState } from "react"

import { SnapshotsService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import type { SnapshotTableData } from "@/components/Snapshots/SnapshotList/columns"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface DeleteSnapshotProps {
  id: string
  onSuccess?: () => void
  externalOpen?: boolean
  onExternalClose?: () => void
}

const DeleteSnapshot = ({
  id,
  onSuccess = () => {},
  externalOpen,
  onExternalClose,
}: DeleteSnapshotProps) => {
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
    mutationFn: (snapshotId: string) =>
      SnapshotsService.deleteSnapshot({ snapshotId }),
    // When mutate is called:
    onMutate: async (_snapshotId, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({ queryKey: ["snapshots"] })
      // Snapshot the previous value
      const previousSnapshots = context.client.getQueryData<
        Array<SnapshotTableData>
      >(["snapshots"])
      // Optimistically update to the new value
      context.client.setQueryData<Array<SnapshotTableData>>(
        ["snapshots"],
        (old) =>
          (old ?? []).map((p) => (p.id === id ? { ...p, pending: true } : p)),
      )
      // Return a result with the snapshotted value
      return { previousSnapshots }
    },
    onSuccess: (_data, _snapshotId, _onMutateResult, context) => {
      showSuccessToast("The snapshot was deleted successfully")
      onSuccess()
      context.client.setQueryData<Array<SnapshotTableData>>(
        ["snapshots"],
        (old) => old?.filter((p) => p.id !== id),
      )
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (error, _snapshotId, onMutateResult, context) => {
      context.client.setQueryData(
        ["snapshots"],
        onMutateResult?.previousSnapshots,
      )
      handleError.call(showErrorToast, error as any)
    },
    // Always refetch after error or success:
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({ queryKey: ["snapshots"] }),
  })

  return (
    <>
      {externalOpen === undefined && (
        <TooltipIconButton
          label="Delete Snapshot"
          icon={<Trash2 />}
          className="text-destructive hover:text-destructive"
          onClick={() => setIsOpen(true)}
        />
      )}
      <ConfirmDialog
        open={isOpen}
        onOpenChange={setIsOpen}
        title="Delete Snapshot"
        description="This snapshot will be permanently deleted. Are you sure? You will not be able to undo this action."
        confirmLabel="Delete"
        onConfirm={() => mutation.mutate(id)}
      />
    </>
  )
}

export default DeleteSnapshot
