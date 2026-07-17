import { createFileRoute, redirect } from "@tanstack/react-router"
import { Puzzle } from "lucide-react"

import { PluginsService } from "@/client"
import {
  MediaListPage,
  serializeTableQuery,
  validateMediaSearch,
} from "@/components/Common/DataTable"
import AddPlugin from "@/components/Plugins/Add"
import {
  type PluginTableData,
  pluginColumns,
} from "@/components/Plugins/columns"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/plugins")({
  component: PluginPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  validateSearch: validateMediaSearch,
  head: () => ({
    meta: [{ title: "Plugins - Stream Channeler" }],
  }),
})

function PluginPage() {
  return (
    <MediaListPage<PluginTableData>
      title="Plugins"
      path="/plugins"
      columns={pluginColumns}
      columnVisibilityKey="plugins-column-visibility"
      defaultHidden={{ key: false, id: false }}
      emptyIcon={Puzzle}
      headerActions={(scope) => (scope === "owned" ? <AddPlugin /> : null)}
      fetchTable={async (scope, params) => {
        const result = await PluginsService.getPlugins({
          scope,
          offset: params.offset,
          limit: params.limit,
          ...serializeTableQuery(params, pluginColumns(scope)),
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
