import DeleteSource from "./DeleteSource"
import EditSource from "./EditSource"
import type { SourceTableData } from "./sourceColumns"

interface SourceActionsMenuProps {
  source: SourceTableData
}

export const SourceActionsMenu = ({ source }: SourceActionsMenuProps) => {
  return (
    <div className="flex items-center justify-end gap-1">
      <EditSource source={source} />
      <DeleteSource source={source} />
    </div>
  )
}
