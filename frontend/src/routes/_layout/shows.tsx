// TODO: Validate
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Clapperboard } from "lucide-react"

import { ShowsService } from "@/client"
import {
  MediaListPage,
  serializeTableQuery,
  validateMediaSearch,
} from "@/components/Common/DataTable"
import { type ShowTableData, showColumns } from "@/components/Shows/columns"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/shows")({
  component: ShowsPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  validateSearch: validateMediaSearch,
  head: () => ({
    meta: [{ title: "Shows - Stream Channeler" }],
  }),
})

function ShowsPage() {
  return (
    <MediaListPage<ShowTableData>
      title="Shows"
      path="/shows"
      columns={showColumns}
      columnVisibilityKey="shows-column-visibility"
      defaultHidden={{ key: false, id: false }}
      emptyIcon={Clapperboard}
      fetchTable={async (scope, params) => {
        const result = await ShowsService.getShows({
          scope,
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
    />
  )
}
