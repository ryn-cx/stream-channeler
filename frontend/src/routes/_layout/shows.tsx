// TODO: Validate
import { createFileRoute } from "@tanstack/react-router"
import { Clapperboard } from "lucide-react"

import { CanonicalShowsService, ShowsService } from "@/client"
import {
  MediaListPage,
  serializeTableQuery,
  validateMediaSearch,
} from "@/components/Common/DataTable"
import AddShow from "@/components/Shows/Add"
import {
  type CanonicalShowTableData,
  canonicalShowColumns,
} from "@/components/Shows/canonicalColumns"
import { type ShowTableData, showColumns } from "@/components/Shows/columns"
import { requireSuperuser } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/shows")({
  component: ShowsPage,
  beforeLoad: requireSuperuser,
  validateSearch: validateMediaSearch,
  head: () => ({
    meta: [{ title: "Shows - Stream Channeler" }],
  }),
})

// TODO: Validate
function ShowsPage() {
  const { source_id } = Route.useSearch()

  return (
    <MediaListPage<ShowTableData, CanonicalShowTableData>
      title="Shows"
      path="/shows"
      columns={showColumns}
      columnVisibilityKey="shows-column-visibility"
      defaultHidden={{ key: false, id: false }}
      emptyIcon={Clapperboard}
      headerActions={source_id ? <AddShow sourceKey={source_id} /> : undefined}
      fetchTable={async (params) => {
        const result = await ShowsService.getShows({
          offset: params.offset,
          limit: params.limit,
          ...serializeTableQuery(params, showColumns),
        })
        return {
          data: result.data,
          total_count: result.total_count,
          filtered_count: result.filtered_count,
          is_server_side: result.is_server_side,
        }
      }}
      canonical={{
        columns: canonicalShowColumns,
        defaultHidden: { id: false },
        fetchTable: async (params) => {
          const result = await CanonicalShowsService.getCanonicalShows({
            offset: params.offset,
            limit: params.limit,
            ...serializeTableQuery(params, canonicalShowColumns),
          })
          return {
            data: result.data,
            total_count: result.total_count,
            filtered_count: result.filtered_count,
            is_server_side: result.is_server_side,
          }
        },
      }}
    />
  )
}
