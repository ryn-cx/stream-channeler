// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { useState } from "react"

import { OpenAPI } from "@/client"
import { request } from "@/client/core/request"
import { DeleteConfirmContent } from "@/components/Common/DeleteConfirmContent"
import { DeleteIconTrigger } from "@/components/Common/DeleteIconTrigger"
import { Dialog } from "@/components/ui/dialog"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

import type { PluginTableData } from "./columns"

type PluginsData = Array<PluginTableData>

interface DeletePluginProps {
  plugin: PluginTableData
}

const DeletePlugin = ({ plugin }: DeletePluginProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: (pluginId: string) =>
      request(OpenAPI, {
        method: "DELETE",
        url: "/api/v1/plugins/{plugin_id}",
        path: { plugin_id: pluginId },
      }),
    onMutate: async (_pluginId, context) => {
      await context.client.cancelQueries({ queryKey: ["plugins"] })
      const previous = context.client.getQueryData<PluginsData>(["plugins"])

      context.client.setQueryData<PluginsData>(["plugins"], (old) =>
        old!.filter((p) => p.id !== plugin.id),
      )

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

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DeleteIconTrigger tooltip="Delete plugin" />
      <DeleteConfirmContent
        title="Delete Plugin"
        description={
          <>
            All data associated with this plugin will be{" "}
            <strong>permanently deleted.</strong> Are you sure? You will not be
            able to undo this action.
          </>
        }
        isPending={mutation.isPending}
        onSubmit={() => mutation.mutate(plugin.id)}
      />
    </Dialog>
  )
}

export default DeletePlugin
