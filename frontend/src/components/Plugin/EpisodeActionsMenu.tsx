import DeleteEpisode from "./DeleteEpisode"
import EditEpisode from "./EditEpisode"
import type { EpisodeTableData } from "./episodeColumns"

interface EpisodeActionsMenuProps {
  episode: EpisodeTableData
}

export const EpisodeActionsMenu = ({ episode }: EpisodeActionsMenuProps) => {
  return (
    <div className="flex items-center justify-end gap-1">
      <EditEpisode episode={episode} />
      <DeleteEpisode episode={episode} />
    </div>
  )
}
