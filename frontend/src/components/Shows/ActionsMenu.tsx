// TODO: Validate
import { ActionsMenu } from "@/components/Common/ActionsMenu"
import type { ShowTableData } from "./columns"
import DeleteShow from "./Delete"
import EditShow from "./Edit"

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
