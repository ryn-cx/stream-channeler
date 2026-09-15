// TODO: Validate
import { ActionsMenu } from "@/components/Common/ActionsMenu"
import { ManageTitlesButton } from "../ChannelDetail/AddUrlsToQueueButton"
import type { ChannelTableData } from "./columns"
import EditChannel from "./EditChannel"

interface ChannelActionsMenuProps {
  channel: ChannelTableData
}

// TODO: Validate
export const ChannelActionsMenu = ({ channel }: ChannelActionsMenuProps) => {
  return (
    <ActionsMenu>
      <EditChannel channel={channel} />
      <ManageTitlesButton
        channelId={channel.id}
        channelName={channel.name}
        variant="icon"
      />
    </ActionsMenu>
  )
}
