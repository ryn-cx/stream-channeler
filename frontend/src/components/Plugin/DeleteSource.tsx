// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { useParams } from "@tanstack/react-router"
import { Trash2 } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"

import { OpenAPI } from "@/client"
import { request } from "@/client/core/request"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

import type { SourceTableData } from "./sourceColumns"

interface SourcesListOutput {
  data: SourceTableData[]
  count: number
}

interface DeleteSourceProps {
  source: SourceTableData
}

const DeleteSource = ({ source }: DeleteSourceProps) => {
  const { pluginKey } = useParams({ strict: false })
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const { handleSubmit } = useForm()

  const mutation = useMutation({
    mutationFn: (sourceId: string) =>
      request(OpenAPI, {
        method: "DELETE",
        url: "/api/v1/sources/{source_id}",
        path: { source_id: sourceId },
      }),
    onMutate: async (_sourceKey, context) => {
      const queryKey = ["plugins", pluginKey, "sources"]
      await context.client.cancelQueries({ queryKey })
      const previous = context.client.getQueryData<SourcesListOutput>(queryKey)

      context.client.setQueryData<SourcesListOutput>(queryKey, (old) => ({
        ...old!,
        data: old!.data.filter((s) => s.key !== source.key),
        count: old!.count - 1,
      }))

      return { previous }
    },
    onSuccess: () => {
      showSuccessToast("Source deleted successfully")
      setIsOpen(false)
    },
    onError: (error, _sourceKey, onMutateResult, context) => {
      context.client.setQueryData(
        ["plugins", pluginKey, "sources"],
        onMutateResult?.previous,
      )
      handleError.call(showErrorToast, error as any)
    },
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({
        queryKey: ["plugins", pluginKey, "sources"],
      }),
  })

  const onSubmit = () => {
    mutation.mutate(source.id)
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <Tooltip>
        <TooltipTrigger asChild>
          <DialogTrigger asChild>
            <Button variant="ghost">
              <Trash2 className="text-destructive" />
            </Button>
          </DialogTrigger>
        </TooltipTrigger>
        <TooltipContent>
          <p>Delete source</p>
        </TooltipContent>
      </Tooltip>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Delete Source</DialogTitle>
            <DialogDescription>
              All data associated with this source will be{" "}
              <strong>permanently deleted.</strong> Are you sure? You will not
              be able to undo this action.
            </DialogDescription>
          </DialogHeader>

          <DialogFooter className="mt-4">
            <DialogClose asChild>
              <Button variant="outline" disabled={mutation.isPending}>
                Cancel
              </Button>
            </DialogClose>
            <LoadingButton
              variant="destructive"
              type="submit"
              loading={mutation.isPending}
            >
              Delete
            </LoadingButton>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default DeleteSource
