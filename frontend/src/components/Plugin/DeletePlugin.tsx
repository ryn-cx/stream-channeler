// TODO: Validate
import { useMutation } from "@tanstack/react-query"
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

import type { PluginTableData } from "./columns"

interface PluginsListOutput {
  data: PluginTableData[]
  count: number
}

interface DeletePluginProps {
  plugin: PluginTableData
}

const DeletePlugin = ({ plugin }: DeletePluginProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const { handleSubmit } = useForm()

  const mutation = useMutation({
    mutationFn: (pluginId: string) =>
      request(OpenAPI, {
        method: "DELETE",
        url: "/api/v1/plugins/{plugin_id}",
        path: { plugin_id: pluginId },
      }),
    onMutate: async (_pluginId, context) => {
      await context.client.cancelQueries({ queryKey: ["plugins"] })
      const previous = context.client.getQueryData<PluginsListOutput>([
        "plugins",
      ])

      context.client.setQueryData<PluginsListOutput>(["plugins"], (old) => ({
        ...old!,
        data: old!.data.filter((p) => p.id !== plugin.id),
        count: old!.count - 1,
      }))

      return { previous }
    },
    onSuccess: () => {
      showSuccessToast("Plugin deleted successfully")
      setIsOpen(false)
    },
    onError: (error, _pluginId, onMutateResult, context) => {
      context.client.setQueryData(["plugins"], onMutateResult?.previous)
      handleError.call(showErrorToast, error as any)
    },
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({ queryKey: ["plugins"] }),
  })

  const onSubmit = () => {
    mutation.mutate(plugin.id)
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
          <p>Delete plugin</p>
        </TooltipContent>
      </Tooltip>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Delete Plugin</DialogTitle>
            <DialogDescription>
              All data associated with this plugin will be{" "}
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

export default DeletePlugin
