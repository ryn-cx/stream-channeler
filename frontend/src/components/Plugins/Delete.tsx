// TODO: Validate
import { Trash2 } from "lucide-react"
import { useState } from "react"

import { PluginsService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { useDeleteTableRow } from "@/components/Common/useDeleteTableRow"

import type { PluginTableData } from "./columns"

interface DeletePluginProps {
  plugin: PluginTableData
}

const DeletePlugin = ({ plugin }: DeletePluginProps) => {
  const [isOpen, setIsOpen] = useState(false)

  const mutation = useDeleteTableRow({
    mutationFn: (pluginId: string) => PluginsService.deletePlugin({ pluginId }),
    rowId: plugin.id,
    successMessage: "Plugin deleted successfully",
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
