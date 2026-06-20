import { ActionsMenu } from "@/components/Common/ActionsMenu"
import type { PluginTableData } from "./columns"
import DeletePlugin from "./DeletePlugin"
import EditPlugin from "./EditPlugin"

interface PluginActionsMenuProps {
  plugin: PluginTableData
}

export const PluginActionsMenu = ({ plugin }: PluginActionsMenuProps) => {
  return (
    <ActionsMenu>
      <EditPlugin plugin={plugin} />
      <DeletePlugin plugin={plugin} />
    </ActionsMenu>
  )
}
