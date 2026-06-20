import { ActionsMenu } from "@/components/Common/ActionsMenu"
import DeleteSource from "./DeleteSource"
import EditSource from "./EditSource"
import type { SourceTableData } from "./sourceColumns"

interface SourceActionsMenuProps {
  source: SourceTableData
}

export const SourceActionsMenu = ({ source }: SourceActionsMenuProps) => {
  return (
    <ActionsMenu>
      <EditSource source={source} />
      <DeleteSource source={source} />
    </ActionsMenu>
  )
}
