// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { useParams } from "@tanstack/react-router"
import { Trash2 } from "lucide-react"
import { useState } from "react"

import { SeasonsService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

import type { SeasonTableData } from "./columns"

type SeasonsData = Array<SeasonTableData>

interface DeleteSeasonProps {
  season: SeasonTableData
}

const DeleteSeason = ({ season }: DeleteSeasonProps) => {
  const { showKey } = useParams({ strict: false })
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryKey = ["shows", showKey, "seasons"]

  const mutation = useMutation({
    mutationFn: (seasonId: string) => SeasonsService.deleteSeason({ seasonId }),
    // When mutate is called:
    onMutate: async (_seasonKey, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({ queryKey })
      // Snapshot the previous value
      const previous = context.client.getQueryData<SeasonsData>(queryKey)

      // Optimistically update to the new value
      context.client.setQueryData<SeasonsData>(queryKey, (old) =>
        old!.map((s) => (s.id === season.id ? { ...s, pending: true } : s)),
      )

      // Return a result with the snapshotted value
      return { previous }
    },
    onSuccess: (_data, _variables, _onMutateResult, context) => {
      showSuccessToast("Season deleted successfully")
      context.client.setQueryData<SeasonsData>(queryKey, (old) =>
        old?.filter((s) => s.id !== season.id),
      )
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (error, _seasonKey, onMutateResult, context) => {
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
