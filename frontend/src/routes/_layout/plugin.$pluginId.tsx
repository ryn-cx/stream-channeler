import { createFileRoute, redirect } from "@tanstack/react-router"
import { Database } from "lucide-react"

import { PluginsService } from "@/client"
import {
  DetailTablePage,
  serializeTableQuery,
} from "@/components/Common/DataTable"
import AddSource from "@/components/Sources/Add"
import {
  type SourceTableData,
  sourceColumns,
} from "@/components/Sources/columns"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/plugin/$pluginId")({
  component: PluginDetailPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Plugin Sources - Stream Channeler" }],
  }),
})

function PluginDetailPage() {
  const { pluginId } = Route.useParams()

  return (
    <DetailTablePage<SourceTableData>
      title="Sources"
      columns={sourceColumns}
      queryKey={["plugins", pluginId, "sources"]}
      fetchTable={async (params) => {
        const result = await PluginsService.getPluginSources({
          pluginId,
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
      columnVisibilityKey="sources-column-visibility"
      emptyIcon={Database}
      emptyTitle="This plugin has no sources yet"
      emptyDescription="Add a source to get started"
      headerActions={<AddSource pluginId={pluginId} />}
    />
  )
}
