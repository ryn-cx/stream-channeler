import { ManageShowsButton } from "../ChannelDetail/AddUrlsToQueueButton"
import type { ChannelTableData } from "./columns"
import DeleteChannel from "./DeleteChannel"
import EditChannel from "./EditChannel"

interface ChannelActionsMenuProps {
  channel: ChannelTableData
}

export const ChannelActionsMenu = ({ channel }: ChannelActionsMenuProps) => {
  return (
    <div className="flex items-center justify-end gap-1">
      <EditChannel channel={channel} />
      <ManageShowsButton channelId={channel.id} variant="icon" />
      <DeleteChannel id={channel.id} />
    </div>
  )
}
