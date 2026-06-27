import { ActionsMenu } from "@/components/Common/ActionsMenu"
import type { EpisodeTableData } from "./columns"
import DeleteEpisode from "./Delete"
import EditEpisode from "./Edit"

interface EpisodeActionsMenuProps {
  episode: EpisodeTableData
}

export const EpisodeActionsMenu = ({ episode }: EpisodeActionsMenuProps) => {
  return (
    <ActionsMenu>
      <EditEpisode episode={episode} />
      <DeleteEpisode episode={episode} />
    </ActionsMenu>
  )
}
