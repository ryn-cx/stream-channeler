// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { useParams } from "@tanstack/react-router"
import { Trash2 } from "lucide-react"
import { useState } from "react"

import { FilesService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

import type { FileTableData } from "./columns"

type FilesData = Array<FileTableData>

interface DeleteFileProps {
  file: FileTableData
}

const DeleteFile = ({ file }: DeleteFileProps) => {
  const { pluginId } = useParams({ strict: false })
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryKey = ["plugins", pluginId, "files"]

  const mutation = useMutation({
    mutationFn: (fileId: string) => FilesService.deleteFile({ fileId }),
    // When mutate is called:
    onMutate: async (_fileId, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({ queryKey })
      // Snapshot the previous value
      const previous = context.client.getQueriesData<FilesData>({ queryKey })

      // Optimistically update to the new value
      context.client.setQueriesData<FilesData>({ queryKey }, (old) =>
        old?.map((existing) =>
          existing.id === file.id ? { ...existing, pending: true } : existing,
        ),
      )

      // Return a result with the snapshotted value
      return { previous }
    },
    onSuccess: (_data, _variables, _onMutateResult, context) => {
      showSuccessToast("File deleted successfully")
      context.client.setQueriesData<FilesData>({ queryKey }, (old) =>
        old?.filter((existing) => existing.id !== file.id),
      )
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (error, _fileId, onMutateResult, context) => {
      for (const [key, data] of onMutateResult?.previous ?? []) {
        context.client.setQueryData(key, data)
      }
      handleError.call(showErrorToast, error as any)
    },
    // Always refetch after error or success:
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({ queryKey }),
  })

  return (
    <>
      <TooltipIconButton
        label="Delete File"
        icon={<Trash2 />}
        className="text-destructive hover:text-destructive"
        onClick={() => setIsOpen(true)}
      />
      <ConfirmDialog
        open={isOpen}
        onOpenChange={setIsOpen}
        title="Delete File"
        description={
          <>
            All data associated with this file will be{" "}
            <strong>permanently deleted.</strong> Are you sure? You will not be
            able to undo this action.
          </>
        }
        confirmLabel="Delete"
        onConfirm={() => mutation.mutate(file.id)}
      />
    </>
  )
}

export default DeleteFile
