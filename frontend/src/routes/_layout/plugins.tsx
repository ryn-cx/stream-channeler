import { createFileRoute, redirect } from "@tanstack/react-router"
import { Puzzle } from "lucide-react"

import { PluginsService } from "@/client"
import {
  MediaListPage,
  serializeTableQuery,
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
  head: () => ({
    meta: [{ title: "Plugins - Stream Channeler" }],
  }),
})

function PluginPage() {
  return (
    <MediaListPage<PluginTableData>
      title="Plugins"
      columns={pluginColumns}
      columnVisibilityKey="plugins-column-visibility"
      defaultHidden={{ key: false, id: false }}
      emptyIcon={Puzzle}
      headerActions={(owner) => (owner === undefined ? <AddPlugin /> : null)}
      fetchTable={async (owner, params) => {
        const result = await PluginsService.getPlugins({
          owner,
          offset: params.offset,
          limit: params.limit,
          ...serializeTableQuery(params, pluginColumns(owner)),
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
