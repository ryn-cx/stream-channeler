import DeleteShow from "./DeleteShow"
import EditShow from "./EditShow"
import type { ShowTableData } from "./showColumns"

interface ShowActionsMenuProps {
  show: ShowTableData
}

export const ShowActionsMenu = ({ show }: ShowActionsMenuProps) => {
  return (
    <div className="flex items-center justify-end gap-1">
      <EditShow show={show} />
      <DeleteShow show={show} />
    </div>
  )
}
