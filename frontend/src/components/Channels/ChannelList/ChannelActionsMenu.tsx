// TODO: Validate
import { ActionsMenu } from "@/components/Common/ActionsMenu"
import { ManageShowsButton } from "../ChannelDetail/AddUrlsToQueueButton"
import type { ChannelTableData } from "./columns"
import DeleteChannel from "./DeleteChannel"
import EditChannel from "./EditChannel"

interface ChannelActionsMenuProps {
  channel: ChannelTableData
}

// TODO: Validate
export const ChannelActionsMenu = ({ channel }: ChannelActionsMenuProps) => {
  return (
    <ActionsMenu>
      <EditChannel channel={channel} />
      <ManageShowsButton
        channelId={channel.id}
        channelName={channel.name}
        variant="icon"
      />
      <DeleteChannel id={channel.id} />
    </ActionsMenu>
  )
}
