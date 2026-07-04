// TODO: Validate
import { Trash2 } from "lucide-react"
import { useState } from "react"

import { ShowsService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { useDeleteTableRow } from "@/components/Common/useDeleteTableRow"

import type { ShowTableData } from "./columns"

interface DeleteShowProps {
  show: ShowTableData
}

const DeleteShow = ({ show }: DeleteShowProps) => {
  const [isOpen, setIsOpen] = useState(false)

  const mutation = useDeleteTableRow({
    mutationFn: (showId: string) => ShowsService.deleteShow({ showId }),
    rowId: show.id,
    successMessage: "Show deleted successfully",
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
