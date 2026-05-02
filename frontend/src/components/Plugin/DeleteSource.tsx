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

import type { SourceTableData } from "./sourceColumns"

type SourcesData = Array<SourceTableData>

interface DeleteSourceProps {
  source: SourceTableData
}

const DeleteSource = ({ source }: DeleteSourceProps) => {
  const { pluginId } = useParams({ strict: false })
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryKey = ["plugins", pluginId, "sources"]

  const mutation = useMutation({
    mutationFn: (sourceId: string) =>
      request(OpenAPI, {
        method: "DELETE",
        url: "/api/v1/sources/{source_id}",
        path: { source_id: sourceId },
      }),
    onMutate: async (_sourceKey, context) => {
      await context.client.cancelQueries({ queryKey })
      const previous = context.client.getQueryData<SourcesData>(queryKey)

      context.client.setQueryData<SourcesData>(queryKey, (old) =>
        old!.filter((s) => s.key !== source.key),
      )

      return { previous }
    },
    onSuccess: () => {
      showSuccessToast("Source deleted successfully")
      setIsOpen(false)
    },
    onError: (error, _sourceKey, onMutateResult, context) => {
      context.client.setQueryData(queryKey, onMutateResult?.previous)
      handleError.call(showErrorToast, error as any)
    },
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({ queryKey }),
  })

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DeleteIconTrigger tooltip="Delete source" />
      <DeleteConfirmContent
        title="Delete Source"
        description={
          <>
            All data associated with this source will be{" "}
            <strong>permanently deleted.</strong> Are you sure? You will not be
            able to undo this action.
          </>
        }
        isPending={mutation.isPending}
        onSubmit={() => mutation.mutate(source.id)}
      />
    </Dialog>
  )
}

export default DeleteSource
