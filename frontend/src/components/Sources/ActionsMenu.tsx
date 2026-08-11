// TODO: Validate
import { ActionsMenu } from "@/components/Common/ActionsMenu"
import type { SourceTableData } from "./columns"
import DeleteSource from "./Delete"
import EditSource from "./Edit"

interface SourceActionsMenuProps {
  source: SourceTableData
}

// TODO: Validate
export const SourceActionsMenu = ({ source }: SourceActionsMenuProps) => {
  return (
    <ActionsMenu>
      <EditSource source={source} />
      <DeleteSource source={source} />
    </ActionsMenu>
  )
}
