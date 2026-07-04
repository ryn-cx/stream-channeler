// TODO: Validate
import { Trash2 } from "lucide-react"
import { useState } from "react"

import { SourcesService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { useDeleteTableRow } from "@/components/Common/useDeleteTableRow"

import type { SourceTableData } from "./columns"

interface DeleteSourceProps {
  source: SourceTableData
}

const DeleteSource = ({ source }: DeleteSourceProps) => {
  const [isOpen, setIsOpen] = useState(false)

  const mutation = useDeleteTableRow({
    mutationFn: (sourceId: string) => SourcesService.deleteSource({ sourceId }),
    rowId: source.id,
    successMessage: "Source deleted successfully",
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
