import { ActionsMenu } from "@/components/Common/ActionsMenu"
import DeleteSeason from "./DeleteSeason"
import EditSeason from "./EditSeason"
import type { SeasonTableData } from "./seasonColumns"

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
