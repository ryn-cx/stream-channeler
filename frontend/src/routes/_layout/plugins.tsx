// TODO: Validate
import { createFileRoute } from "@tanstack/react-router"
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
import useAuth, { requireSuperuser } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/plugins")({
  component: PluginPage,
  beforeLoad: requireSuperuser,
  validateSearch: validateMediaSearch,
  head: () => ({
    meta: [{ title: "Plugins - Stream Channeler" }],
  }),
})

// TODO: Validate
function PluginPage() {
  const { user } = useAuth()
  const isAdmin = user?.is_superuser ?? false

  return (
    <MediaListPage<PluginTableData>
      title="Plugins"
      path="/plugins"
      columns={pluginColumns(isAdmin)}
      columnVisibilityKey="plugins-column-visibility"
      defaultHidden={{ key: false, id: false }}
      emptyIcon={Puzzle}
      headerActions={<AddPlugin />}
      fetchTable={async (params) => {
        const result = await PluginsService.getPlugins({
          offset: params.offset,
          limit: params.limit,
          ...serializeTableQuery(params, pluginColumns(isAdmin)),
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
