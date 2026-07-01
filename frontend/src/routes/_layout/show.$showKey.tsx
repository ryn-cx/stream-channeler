// TODO: Validate
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Layers } from "lucide-react"

import { SeasonsService } from "@/client"
import {
  DetailTablePage,
  serializeTableQuery,
} from "@/components/Common/DataTable"
import AddSeason from "@/components/Seasons/Add"
import {
  type SeasonTableData,
  seasonColumns,
} from "@/components/Seasons/columns"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/show/$showKey")({
  component: ShowDetailPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Show Seasons - Stream Channeler" }],
  }),
})

function ShowDetailPage() {
  const { showKey } = Route.useParams()

  return (
    <DetailTablePage<SeasonTableData>
      title="Seasons"
      columns={seasonColumns}
      queryKey={["shows", showKey, "seasons"]}
      fetchTable={async (params) => {
        const result = await SeasonsService.getShowSeasons({
          showId: showKey,
          offset: params.offset,
          limit: params.limit,
          ...serializeTableQuery(params, seasonColumns),
        })
        return {
          data: result.data,
          total_count: result.total_count,
          filtered_count: result.filtered_count,
          is_server_side: result.is_server_side,
        }
      }}
      columnVisibilityKey="seasons-column-visibility"
      emptyIcon={Layers}
      emptyTitle="This show has no seasons yet"
      emptyDescription="Add a season to get started"
      headerActions={<AddSeason showKey={showKey} />}
    />
  )
}
