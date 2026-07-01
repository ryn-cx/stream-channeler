// TODO: Validate
import { ActionsMenu } from "@/components/Common/ActionsMenu"
import type { SnapshotTableData } from "./columns"
import DeleteSnapshot from "./DeleteSnapshot"
import EditSnapshot from "./EditSnapshot"

interface SnapshotActionsMenuProps {
  snapshot: SnapshotTableData
}

export const SnapshotActionsMenu = ({ snapshot }: SnapshotActionsMenuProps) => {
  return (
    <ActionsMenu>
      <EditSnapshot snapshot={snapshot} />
      <DeleteSnapshot id={snapshot.id} />
    </ActionsMenu>
  )
}
