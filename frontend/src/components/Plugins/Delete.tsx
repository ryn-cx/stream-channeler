// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { Trash2 } from "lucide-react"
import { useState } from "react"

import { PluginsService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
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
    mutationFn: (pluginId: string) => PluginsService.deletePlugin({ pluginId }),
    // When mutate is called:
    onMutate: async (_pluginId, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({ queryKey: ["plugins"] })
      // Snapshot the previous value
      const previous = context.client.getQueryData<PluginsData>(["plugins"])

      // Optimistically update to the new value
      context.client.setQueryData<PluginsData>(["plugins"], (old) =>
        old!.map((p) => (p.id === plugin.id ? { ...p, pending: true } : p)),
      )

      // Return a result with the snapshotted value
      return { previous }
    },
    onSuccess: (_data, _variables, _onMutateResult, context) => {
      showSuccessToast("Plugin deleted successfully")
      context.client.setQueryData<PluginsData>(["plugins"], (old) =>
        old?.filter((p) => p.id !== plugin.id),
      )
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (error, _pluginId, onMutateResult, context) => {
      context.client.setQueryData(["plugins"], onMutateResult?.previous)
      handleError.call(showErrorToast, error as any)
    },
    // Always refetch after error or success:
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({ queryKey: ["plugins"] }),
  })

  return (
    <>
      <TooltipIconButton
        label="Delete Plugin"
        icon={<Trash2 />}
        className="text-destructive hover:text-destructive"
        onClick={() => setIsOpen(true)}
      />
      <ConfirmDialog
        open={isOpen}
        onOpenChange={setIsOpen}
        title="Delete Plugin"
        description={
          <>
            All data associated with this plugin will be{" "}
            <strong>permanently deleted.</strong> Are you sure? You will not be
            able to undo this action.
          </>
        }
        confirmLabel="Delete"
        onConfirm={() => mutation.mutate(plugin.id)}
      />
    </>
  )
}

export default DeletePlugin
