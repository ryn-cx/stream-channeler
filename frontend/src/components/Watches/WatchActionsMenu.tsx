// TODO: Validate

import CompleteWatch from "./CompleteWatch"
import type { WatchWithDetails } from "./columns"
import DeleteWatch from "./DeleteWatch"
import EditWatch from "./EditWatch"

interface WatchActionsMenuProps {
  watch: WatchWithDetails
}

// TODO: Validate
export const WatchActionsMenu = ({ watch }: WatchActionsMenuProps) => {
  return (
    <div className="flex items-center justify-end gap-1">
      <CompleteWatch id={watch.id} completed={watch.completed} />
      <EditWatch watch={watch} />
      <DeleteWatch id={watch.id} />
    </div>
  )
}
