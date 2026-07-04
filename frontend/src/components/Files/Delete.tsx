// TODO: Validate
import { Trash2 } from "lucide-react"
import { useState } from "react"

import { FilesService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { useDeleteTableRow } from "@/components/Common/useDeleteTableRow"

import type { FileTableData } from "./columns"

interface DeleteFileProps {
  file: FileTableData
}

const DeleteFile = ({ file }: DeleteFileProps) => {
  const [isOpen, setIsOpen] = useState(false)

  const mutation = useDeleteTableRow({
    mutationFn: (fileId: string) => FilesService.deleteFile({ fileId }),
    rowId: file.id,
    successMessage: "File deleted successfully",
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
