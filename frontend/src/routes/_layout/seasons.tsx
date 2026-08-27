// TODO: Validate
import { createFileRoute } from "@tanstack/react-router"
import { Layers } from "lucide-react"

import { SeasonsService } from "@/client"
import {
  MediaListPage,
  serializeTableQuery,
  validateMediaSearch,
} from "@/components/Common/DataTable"
import AddSeason from "@/components/Seasons/Add"
import {
  type SeasonTableData,
  seasonColumns,
} from "@/components/Seasons/columns"
import { requireSuperuser } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/seasons")({
  component: SeasonsPage,
  beforeLoad: requireSuperuser,
  validateSearch: validateMediaSearch,
  head: () => ({
    meta: [{ title: "Seasons - Stream Channeler" }],
  }),
})

// TODO: Validate
function SeasonsPage() {
  const { show_id } = Route.useSearch()

  return (
    <MediaListPage<SeasonTableData>
      title="Seasons"
      path="/seasons"
      columns={seasonColumns}
      columnVisibilityKey="seasons-column-visibility"
      defaultHidden={{ key: false, id: false }}
      emptyIcon={Layers}
      headerActions={show_id ? <AddSeason showKey={show_id} /> : undefined}
      fetchTable={async (params) => {
        const result = await SeasonsService.getSeasons({
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
    />
  )
}
