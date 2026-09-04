// TODO: Validate
import { ActionsMenu } from "@/components/Common/ActionsMenu"
import type { ShowTableData } from "./columns"
import EditShow from "./Edit"

interface ShowActionsMenuProps {
  show: ShowTableData
}

// TODO: Validate
export const ShowActionsMenu = ({ show }: ShowActionsMenuProps) => {
  return (
    <ActionsMenu>
      <EditShow show={show} />
    </ActionsMenu>
  )
}
