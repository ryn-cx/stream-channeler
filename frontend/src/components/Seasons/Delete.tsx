// TODO: Validate
import { Trash2 } from "lucide-react"
import { useState } from "react"

import { SeasonsService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { useDeleteTableRow } from "@/components/Common/useDeleteTableRow"

import type { SeasonTableData } from "./columns"

interface DeleteSeasonProps {
  season: SeasonTableData
}

const DeleteSeason = ({ season }: DeleteSeasonProps) => {
  const [isOpen, setIsOpen] = useState(false)

  const mutation = useDeleteTableRow({
    mutationFn: (seasonId: string) => SeasonsService.deleteSeason({ seasonId }),
    rowId: season.id,
    successMessage: "Season deleted successfully",
  })

  return (
    <>
      <TooltipIconButton
        label="Delete Season"
        icon={<Trash2 />}
        className="text-destructive hover:text-destructive"
        onClick={() => setIsOpen(true)}
      />
      <ConfirmDialog
        open={isOpen}
        onOpenChange={setIsOpen}
        title="Delete Season"
        description={
          <>
            All data associated with this season will be{" "}
            <strong>permanently deleted.</strong> Are you sure? You will not be
            able to undo this action.
          </>
        }
        confirmLabel="Delete"
        onConfirm={() => mutation.mutate(season.id)}
      />
    </>
  )
}

export default DeleteSeason
