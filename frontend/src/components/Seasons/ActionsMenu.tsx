import { ActionsMenu } from "@/components/Common/ActionsMenu"
import type { SeasonTableData } from "./columns"
import DeleteSeason from "./Delete"
import EditSeason from "./Edit"

interface SeasonActionsMenuProps {
  season: SeasonTableData
}

export const SeasonActionsMenu = ({ season }: SeasonActionsMenuProps) => {
  return (
    <ActionsMenu>
      <EditSeason season={season} />
      <DeleteSeason season={season} />
    </ActionsMenu>
  )
}
