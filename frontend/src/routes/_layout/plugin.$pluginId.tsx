// TODO: Validate
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Database } from "lucide-react"

import { SourcesService } from "@/client"
import {
  DetailTablePage,
  serializeTableQuery,
} from "@/components/Common/DataTable"
import { DetailBreadcrumb } from "@/components/Common/DetailBreadcrumb"
import AddSource from "@/components/Sources/Add"
import {
  type SourceTableData,
  sourceColumns,
} from "@/components/Sources/columns"
import { isLoggedIn } from "@/hooks/useAuth"
import { usePlugin } from "@/hooks/useEntities"

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

// TODO: Validate
function PluginDetailPage() {
  const { pluginId } = Route.useParams()
  const { data: plugin } = usePlugin(pluginId)

  return (
    <DetailTablePage<SourceTableData>
      title={
        <DetailBreadcrumb plugin={plugin} trailing="Sources" current="plugin" />
      }
      columns={sourceColumns}
      queryKey={["plugins", pluginId, "sources"]}
      fetchTable={async (params) => {
        const result = await SourcesService.getPluginSources({
          pluginId,
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
      columnVisibilityKey="sources-column-visibility"
      emptyIcon={Database}
      emptyTitle="This plugin has no sources yet"
      emptyDescription="Add a source to get started"
      headerActions={<AddSource pluginId={pluginId} />}
    />
  )
}
