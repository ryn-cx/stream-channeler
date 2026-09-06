// TODO: Validate
import { ActionsMenu } from "@/components/Common/ActionsMenu"
import type { TitleTableData } from "./columns"
import EditTitle from "./Edit"

interface TitleActionsMenuProps {
  title: TitleTableData
}

// TODO: Validate
export const TitleActionsMenu = ({ title }: TitleActionsMenuProps) => {
  return (
    <ActionsMenu>
      <EditTitle title={title} />
    </ActionsMenu>
  )
}
