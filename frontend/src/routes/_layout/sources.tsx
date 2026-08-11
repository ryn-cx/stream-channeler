// TODO: Validate
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Database } from "lucide-react"

import { SourcesService } from "@/client"
import {
  MediaListPage,
  serializeTableQuery,
  validateMediaSearch,
} from "@/components/Common/DataTable"
import {
  type SourceTableData,
  sourceColumns,
} from "@/components/Sources/columns"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/sources")({
  component: SourcesPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  validateSearch: validateMediaSearch,
  head: () => ({
    meta: [{ title: "Sources - Stream Channeler" }],
  }),
})

// TODO: Validate
function SourcesPage() {
  return (
    <MediaListPage<SourceTableData>
      title="Sources"
      path="/sources"
      columns={sourceColumns}
      columnVisibilityKey="sources-column-visibility"
      defaultHidden={{ key: false, id: false }}
      emptyIcon={Database}
      fetchTable={async (scope, params) => {
        const result = await SourcesService.getSources({
          scope,
          offset: params.offset,
          limit: params.limit,
          ...serializeTableQuery(params, sourceColumns),
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
