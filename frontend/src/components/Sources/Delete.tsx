// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { useParams } from "@tanstack/react-router"
import { Trash2 } from "lucide-react"
import { useState } from "react"

import { SourcesService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

import type { SourceTableData } from "./columns"

type SourcesData = Array<SourceTableData>

interface DeleteSourceProps {
  source: SourceTableData
}

const DeleteSource = ({ source }: DeleteSourceProps) => {
  const { pluginId } = useParams({ strict: false })
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryKey = ["plugins", pluginId, "sources"]

  const mutation = useMutation({
    mutationFn: (sourceId: string) => SourcesService.deleteSource({ sourceId }),
    // When mutate is called:
    onMutate: async (_sourceKey, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({ queryKey })
      // Snapshot the previous value
      const previous = context.client.getQueryData<SourcesData>(queryKey)

      // Optimistically update to the new value
      context.client.setQueryData<SourcesData>(queryKey, (old) =>
        old!.map((s) => (s.id === source.id ? { ...s, pending: true } : s)),
      )

      // Return a result with the snapshotted value
      return { previous }
    },
    onSuccess: (_data, _variables, _onMutateResult, context) => {
      showSuccessToast("Source deleted successfully")
      context.client.setQueryData<SourcesData>(queryKey, (old) =>
        old?.filter((s) => s.id !== source.id),
      )
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (error, _sourceKey, onMutateResult, context) => {
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
        label="Delete Source"
        icon={<Trash2 />}
        className="text-destructive hover:text-destructive"
        onClick={() => setIsOpen(true)}
      />
      <ConfirmDialog
        open={isOpen}
        onOpenChange={setIsOpen}
        title="Delete Source"
        description={
          <>
            All data associated with this source will be{" "}
            <strong>permanently deleted.</strong> Are you sure? You will not be
            able to undo this action.
          </>
        }
        confirmLabel="Delete"
        onConfirm={() => mutation.mutate(source.id)}
      />
    </>
  )
}

export default DeleteSource
