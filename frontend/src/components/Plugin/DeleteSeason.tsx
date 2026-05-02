// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { useParams } from "@tanstack/react-router"
import { useState } from "react"

import { OpenAPI } from "@/client"
import { request } from "@/client/core/request"
import { DeleteConfirmContent } from "@/components/Common/DeleteConfirmContent"
import { DeleteIconTrigger } from "@/components/Common/DeleteIconTrigger"
import { Dialog } from "@/components/ui/dialog"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

import type { SeasonTableData } from "./seasonColumns"

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
    mutationFn: (seasonId: string) =>
      request(OpenAPI, {
        method: "DELETE",
        url: "/api/v1/seasons/{season_id}",
        path: { season_id: seasonId },
      }),
    onMutate: async (_seasonKey, context) => {
      await context.client.cancelQueries({ queryKey })
      const previous = context.client.getQueryData<SeasonsData>(queryKey)

      context.client.setQueryData<SeasonsData>(queryKey, (old) =>
        old!.filter((s) => s.key !== season.key),
      )

      return { previous }
    },
    onSuccess: () => {
      showSuccessToast("Season deleted successfully")
      setIsOpen(false)
    },
    onError: (error, _seasonKey, onMutateResult, context) => {
      context.client.setQueryData(queryKey, onMutateResult?.previous)
      handleError.call(showErrorToast, error as any)
    },
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({ queryKey }),
  })

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DeleteIconTrigger tooltip="Delete season" />
      <DeleteConfirmContent
        title="Delete Season"
        description={
          <>
            All data associated with this season will be{" "}
            <strong>permanently deleted.</strong> Are you sure? You will not be
            able to undo this action.
          </>
        }
        isPending={mutation.isPending}
        onSubmit={() => mutation.mutate(season.id)}
      />
    </Dialog>
  )
}

export default DeleteSeason
