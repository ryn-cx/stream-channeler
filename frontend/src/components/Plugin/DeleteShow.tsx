// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { useParams } from "@tanstack/react-router"
import { Trash2 } from "lucide-react"
import { useState } from "react"

import { ShowsService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

import type { ShowTableData } from "./showColumns"

type ShowsData = Array<ShowTableData>

interface DeleteShowProps {
  show: ShowTableData
}

const DeleteShow = ({ show }: DeleteShowProps) => {
  const { sourceKey } = useParams({ strict: false })
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryKey = ["sources", sourceKey, "shows"]

  const mutation = useMutation({
    mutationFn: (showId: string) => ShowsService.deleteShow({ showId }),
    // When mutate is called:
    onMutate: async (_showKey, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({ queryKey })
      // Snapshot the previous value
      const previous = context.client.getQueryData<ShowsData>(queryKey)

      // Optimistically update to the new value
      context.client.setQueryData<ShowsData>(queryKey, (old) =>
        old!.map((s) => (s.id === show.id ? { ...s, pending: true } : s)),
      )

      // Return a result with the snapshotted value
      return { previous }
    },
    onSuccess: (_data, _variables, _onMutateResult, context) => {
      showSuccessToast("Show deleted successfully")
      context.client.setQueryData<ShowsData>(queryKey, (old) =>
        old?.filter((s) => s.id !== show.id),
      )
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (error, _showKey, onMutateResult, context) => {
      context.client.setQueryData(queryKey, onMutateResult?.previous)
      handleError.call(showErrorToast, error as any)
    },
    // Always refetch after error or success:
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({ queryKey }),
  })

  return (
    <>
      <TooltipIconButton
        label="Delete Show"
        icon={<Trash2 />}
        className="text-destructive hover:text-destructive"
        onClick={() => setIsOpen(true)}
      />
      <ConfirmDialog
        open={isOpen}
        onOpenChange={setIsOpen}
        title="Delete Show"
        description={
          <>
            All data associated with this show will be{" "}
            <strong>permanently deleted.</strong> Are you sure? You will not be
            able to undo this action.
          </>
        }
        confirmLabel="Delete"
        onConfirm={() => mutation.mutate(show.id)}
      />
    </>
  )
}

export default DeleteShow
