// TODO: Validate
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Film } from "lucide-react"

import { EpisodesService } from "@/client"
import {
  DetailTablePage,
  serializeTableQuery,
} from "@/components/Common/DataTable"
import AddEpisode from "@/components/Episodes/Add"
import {
  type EpisodeTableData,
  episodeColumns,
} from "@/components/Episodes/columns"
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
        const result = await EpisodesService.getSeasonEpisodes({
          seasonId: seasonKey,
          offset: params.offset,
          limit: params.limit,
          ...serializeTableQuery(params),
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
