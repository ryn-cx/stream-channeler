// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { useParams } from "@tanstack/react-router"
import { Trash2 } from "lucide-react"
import { useState } from "react"

import { EpisodesService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

import type { EpisodeTableData } from "./episodeColumns"

type EpisodesData = Array<EpisodeTableData>

interface DeleteEpisodeProps {
  episode: EpisodeTableData
}

const DeleteEpisode = ({ episode }: DeleteEpisodeProps) => {
  const { seasonKey } = useParams({ strict: false })
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryKey = ["seasons", seasonKey, "episodes"]

  const mutation = useMutation({
    mutationFn: (episodeId: string) =>
      EpisodesService.deleteEpisode({ episodeId }),
    // When mutate is called:
    onMutate: async (_episodeKey, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({ queryKey })
      // Snapshot the previous value
      const previous = context.client.getQueryData<EpisodesData>(queryKey)

      // Optimistically update to the new value
      context.client.setQueryData<EpisodesData>(queryKey, (old) =>
        old!.map((e) => (e.id === episode.id ? { ...e, pending: true } : e)),
      )

      // Return a result with the snapshotted value
      return { previous }
    },
    onSuccess: (_data, _variables, _onMutateResult, context) => {
      showSuccessToast("Episode deleted successfully")
      context.client.setQueryData<EpisodesData>(queryKey, (old) =>
        old?.filter((e) => e.id !== episode.id),
      )
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (error, _episodeKey, onMutateResult, context) => {
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
