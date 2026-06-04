import DeleteSeason from "./DeleteSeason"
import EditSeason from "./EditSeason"
import type { SeasonTableData } from "./seasonColumns"

interface SeasonActionsMenuProps {
  season: SeasonTableData
}

export const SeasonActionsMenu = ({ season }: SeasonActionsMenuProps) => {
  return (
    <div className="flex items-center justify-end gap-1">
      <EditSeason season={season} />
      <DeleteSeason season={season} />
    </div>
  )
}
