import { ActionsMenu } from "@/components/Common/ActionsMenu"
import DeleteShow from "./DeleteShow"
import EditShow from "./EditShow"
import type { ShowTableData } from "./showColumns"

interface ShowActionsMenuProps {
  show: ShowTableData
}

export const ShowActionsMenu = ({ show }: ShowActionsMenuProps) => {
  return (
    <ActionsMenu>
      <EditShow show={show} />
      <DeleteShow show={show} />
    </ActionsMenu>
  )
}
