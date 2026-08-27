// TODO: Validate
import { createFileRoute } from "@tanstack/react-router"
import { Database } from "lucide-react"

import { SourcesService } from "@/client"
import {
  MediaListPage,
  serializeTableQuery,
  validateMediaSearch,
} from "@/components/Common/DataTable"
import AddSource from "@/components/Sources/Add"
import {
  type SourceTableData,
  sourceColumns,
} from "@/components/Sources/columns"
import { requireSuperuser } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/sources")({
  component: SourcesPage,
  beforeLoad: requireSuperuser,
  validateSearch: validateMediaSearch,
  head: () => ({
    meta: [{ title: "Sources - Stream Channeler" }],
  }),
})

// TODO: Validate
function SourcesPage() {
  const { plugin_id } = Route.useSearch()

  return (
    <MediaListPage<SourceTableData>
      title="Sources"
      path="/sources"
      columns={sourceColumns}
      columnVisibilityKey="sources-column-visibility"
      defaultHidden={{ key: false, id: false }}
      emptyIcon={Database}
      headerActions={plugin_id ? <AddSource pluginId={plugin_id} /> : undefined}
      fetchTable={async (params) => {
        const result = await SourcesService.getSources({
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
