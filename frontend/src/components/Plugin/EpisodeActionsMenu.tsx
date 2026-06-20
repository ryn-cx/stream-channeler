import { ActionsMenu } from "@/components/Common/ActionsMenu"
import DeleteEpisode from "./DeleteEpisode"
import EditEpisode from "./EditEpisode"
import type { EpisodeTableData } from "./episodeColumns"

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
