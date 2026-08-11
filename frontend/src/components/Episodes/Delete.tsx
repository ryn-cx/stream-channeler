// TODO: Validate
import { Trash2 } from "lucide-react"
import { useState } from "react"

import { EpisodesService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { useDeleteTableRow } from "@/components/Common/useDeleteTableRow"

import type { EpisodeTableData } from "./columns"

interface DeleteEpisodeProps {
  episode: EpisodeTableData
}

// TODO: Validate
const DeleteEpisode = ({ episode }: DeleteEpisodeProps) => {
  const [isOpen, setIsOpen] = useState(false)

  const mutation = useDeleteTableRow({
    mutationFn: (episodeId: string) =>
      EpisodesService.deleteEpisode({ episodeId }),
    rowId: episode.id,
    successMessage: "Episode deleted successfully",
  })

  return (
    <>
      <TooltipIconButton
        label="Delete Episode"
        icon={<Trash2 />}
        className="text-destructive hover:text-destructive"
        onClick={() => setIsOpen(true)}
      />
      <ConfirmDialog
        open={isOpen}
        onOpenChange={setIsOpen}
        title="Delete Episode"
        description={
          <>
            All data associated with this episode will be{" "}
            <strong>permanently deleted.</strong> Are you sure? You will not be
            able to undo this action.
          </>
        }
        confirmLabel="Delete"
        onConfirm={() => mutation.mutate(episode.id)}
      />
    </>
  )
}

export default DeleteEpisode
