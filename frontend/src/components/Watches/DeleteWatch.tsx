// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { Trash2 } from "lucide-react"
import { useState } from "react"

import { type Message, type WatchesListOutput, WatchesService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface DeleteWatchProps {
  id: string
  onSuccess?: () => void
}

const DeleteWatch = ({ id, onSuccess = () => {} }: DeleteWatchProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: (watchId: string) => WatchesService.deleteWatch({ watchId }),
    // When mutate is called:
    onMutate: async (deletedId, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({ queryKey: ["watches"] })

      // Snapshot the previous value
      const previousWatches = context.client.getQueryData<WatchesListOutput>([
        "watches",
      ])

      // Optimistically mark the watch (and siblings with the same plugin,
      // episode key, and watch date) as pending.
      const matchesDeletedSibling = (
        watch: { episode_id: string; watch_date?: string | null },
        deleted: { episode_id: string; watch_date?: string | null },
        old: WatchesListOutput,
      ) => {
        if (watch.watch_date !== deleted.watch_date) return false
        const episode = old.episodes[watch.episode_id]
        const deletedEpisode = old.episodes[deleted.episode_id]
        if (episode.key !== deletedEpisode.key) return false
        const source =
          old.sources[
            old.shows[old.seasons[episode.season_id].show_id].source_id
          ]
        const deletedSource =
          old.sources[
            old.shows[old.seasons[deletedEpisode.season_id].show_id].source_id
          ]
        return source.plugin_id === deletedSource.plugin_id
      }
      context.client.setQueryData<WatchesListOutput>(["watches"], (old) => {
        if (!old) return old
        const deletedWatch = old.watches.find((w) => w.id === deletedId)
        if (!deletedWatch) return old
        return {
          ...old,
          watches: old.watches.map((watch) =>
            matchesDeletedSibling(watch, deletedWatch, old)
              ? ({ ...watch, pending: true } as typeof watch)
              : watch,
          ),
        }
      })

      // Return a result with the snapshotted value
      return { previousWatches }
    },
    onSuccess: (result: Message, deletedId, _onMutateResult, context) => {
      showSuccessToast(result.message)
      onSuccess()
      context.client.setQueryData<WatchesListOutput>(["watches"], (old) => {
        if (!old) return old
        const deletedWatch = old.watches.find((w) => w.id === deletedId)
        if (!deletedWatch) return old
        const deletedEpisode = old.episodes[deletedWatch.episode_id]
        const deletedSource =
          old.sources[
            old.shows[old.seasons[deletedEpisode.season_id].show_id].source_id
          ]
        return {
          ...old,
          watches: old.watches.filter((watch) => {
            if (watch.watch_date !== deletedWatch.watch_date) return true
            const episode = old.episodes[watch.episode_id]
            if (episode.key !== deletedEpisode.key) return true
            const source =
              old.sources[
                old.shows[old.seasons[episode.season_id].show_id].source_id
              ]
            return source.plugin_id !== deletedSource.plugin_id
          }),
        }
      })
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (error, _deletedId, onMutateResult, context) => {
      context.client.setQueryData(["watches"], onMutateResult?.previousWatches)
      handleError.call(showErrorToast, error as any)
    },
    // Always refetch after error or success:
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({ queryKey: ["watches"] }),
  })

  return (
    <>
      <TooltipIconButton
        label="Delete Watch"
        icon={<Trash2 />}
        className="text-destructive hover:text-destructive"
        onClick={() => setIsOpen(true)}
      />
      <ConfirmDialog
        open={isOpen}
        onOpenChange={setIsOpen}
        title="Delete Watch"
        description="This watch entry will be permanently deleted. Are you sure? You will not be able to undo this action."
        confirmLabel="Delete"
        onConfirm={() => mutation.mutate(id)}
      />
    </>
  )
}

export default DeleteWatch
