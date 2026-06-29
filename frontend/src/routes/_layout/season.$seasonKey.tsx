import { createFileRoute, redirect } from "@tanstack/react-router"
import { Film } from "lucide-react"

import { SeasonsService } from "@/client"
import AddEpisode from "@/components/Episodes/Add"
import {
  type EpisodeTableData,
  episodeColumns,
} from "@/components/Episodes/columns"
import { DetailTablePage } from "@/components/Common/DataTable"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/season/$seasonKey")({
  component: SeasonDetailPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Season Episodes - Stream Channeler" }],
  }),
})

function SeasonDetailPage() {
  const { seasonKey } = Route.useParams()

  return (
    <DetailTablePage<EpisodeTableData>
      title="Episodes"
      columns={episodeColumns}
      queryKey={["seasons", seasonKey, "episodes"]}
      fetchTable={async (params) => {
        const result = await SeasonsService.getEpisodes({
          seasonId: seasonKey,
          offset: params.offset,
          limit: params.limit,
          sortOptions: JSON.stringify(params.sorting),
          filterOptions: JSON.stringify(params.columnFilters),
        })
        return {
          data: result.data,
          total_count: result.total_count,
          filtered_count: result.filtered_count,
          is_server_side: result.is_server_side,
        }
      }}
      columnVisibilityKey="episodes-column-visibility"
      emptyIcon={Film}
      emptyTitle="This season has no episodes yet"
      emptyDescription="Add an episode to get started"
      headerActions={<AddEpisode seasonKey={seasonKey} />}
    />
  )
}
