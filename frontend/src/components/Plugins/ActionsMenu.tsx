// TODO: Validate
import { ActionsMenu } from "@/components/Common/ActionsMenu"
import type { PluginTableData } from "./columns"
import DeletePlugin from "./Delete"
import EditPlugin from "./Edit"

interface PluginActionsMenuProps {
  plugin: PluginTableData
}

// TODO: Validate
export const PluginActionsMenu = ({ plugin }: PluginActionsMenuProps) => {
  return (
    <ActionsMenu>
      <EditPlugin plugin={plugin} />
      <DeletePlugin plugin={plugin} />
    </ActionsMenu>
  )
}
