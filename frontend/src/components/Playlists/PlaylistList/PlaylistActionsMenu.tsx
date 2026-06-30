// TODO: Validate
import { ActionsMenu } from "@/components/Common/ActionsMenu"
import type { PlaylistTableData } from "./columns"
import DeletePlaylist from "./DeletePlaylist"
import EditPlaylist from "./EditPlaylist"

interface PlaylistActionsMenuProps {
  playlist: PlaylistTableData
}

export const PlaylistActionsMenu = ({ playlist }: PlaylistActionsMenuProps) => {
  return (
    <ActionsMenu>
      <EditPlaylist playlist={playlist} />
      <DeletePlaylist id={playlist.id} />
    </ActionsMenu>
  )
}
