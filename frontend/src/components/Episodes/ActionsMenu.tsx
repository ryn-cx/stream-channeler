// TODO: Validate
import { ActionsMenu } from "@/components/Common/ActionsMenu"
import type { EpisodeTableData } from "./columns"
import EditEpisode from "./Edit"
import QuickUnlinkEpisode from "./QuickUnlink"
import ToggleIgnoredEpisode from "./ToggleIgnored"

interface EpisodeActionsMenuProps {
  episode: EpisodeTableData
}

// TODO: Validate
export const EpisodeActionsMenu = ({ episode }: EpisodeActionsMenuProps) => {
  return (
    <ActionsMenu>
      <EditEpisode episode={episode} />
      <QuickUnlinkEpisode episode={episode} />
      <ToggleIgnoredEpisode episode={episode} />
    </ActionsMenu>
  )
}
