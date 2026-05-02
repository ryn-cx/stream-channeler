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

import type { ShowTableData } from "./showColumns"

type ShowsData = Array<ShowTableData>

interface DeleteShowProps {
  show: ShowTableData
}

const DeleteShow = ({ show }: DeleteShowProps) => {
  const { sourceKey } = useParams({ strict: false })
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryKey = ["sources", sourceKey, "shows"]

  const mutation = useMutation({
    mutationFn: (showId: string) =>
      request(OpenAPI, {
        method: "DELETE",
        url: "/api/v1/shows/{show_id}",
        path: { show_id: showId },
      }),
    onMutate: async (_showKey, context) => {
      await context.client.cancelQueries({ queryKey })
      const previous = context.client.getQueryData<ShowsData>(queryKey)

      context.client.setQueryData<ShowsData>(queryKey, (old) =>
        old!.filter((s) => s.key !== show.key),
      )

      return { previous }
    },
    onSuccess: () => {
      showSuccessToast("Show deleted successfully")
      setIsOpen(false)
    },
    onError: (error, _showKey, onMutateResult, context) => {
      context.client.setQueryData(queryKey, onMutateResult?.previous)
      handleError.call(showErrorToast, error as any)
    },
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({ queryKey }),
  })

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DeleteIconTrigger tooltip="Delete show" />
      <DeleteConfirmContent
        title="Delete Show"
        description={
          <>
            All data associated with this show will be{" "}
            <strong>permanently deleted.</strong> Are you sure? You will not be
            able to undo this action.
          </>
        }
        isPending={mutation.isPending}
        onSubmit={() => mutation.mutate(show.id)}
      />
    </Dialog>
  )
}

export default DeleteShow
