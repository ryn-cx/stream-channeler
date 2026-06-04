import type { PluginTableData } from "./columns"
import DeletePlugin from "./DeletePlugin"
import EditPlugin from "./EditPlugin"

interface PluginActionsMenuProps {
  plugin: PluginTableData
}

export const PluginActionsMenu = ({ plugin }: PluginActionsMenuProps) => {
  return (
    <div className="flex items-center justify-end gap-1">
      <EditPlugin plugin={plugin} />
      <DeletePlugin plugin={plugin} />
    </div>
  )
}
