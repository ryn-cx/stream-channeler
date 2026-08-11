// TODO: Validate
import type { WatchWithDetails } from "./columns"
import DeleteWatch from "./DeleteWatch"
import EditWatch from "./EditWatch"
import VerifyWatch from "./VerifyWatch"

interface WatchActionsMenuProps {
  watch: WatchWithDetails
}

// TODO: Validate
export const WatchActionsMenu = ({ watch }: WatchActionsMenuProps) => {
  return (
    <div className="flex items-center justify-end gap-1">
      <VerifyWatch id={watch.id} verified={watch.verified} />
      <EditWatch watch={watch} />
      <DeleteWatch id={watch.id} />
    </div>
  )
}
