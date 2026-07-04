// TODO: Validate
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Clapperboard } from "lucide-react"

import { ShowsService } from "@/client"
import {
  DetailTablePage,
  serializeTableQuery,
} from "@/components/Common/DataTable"
import { DetailBreadcrumb } from "@/components/Common/DetailBreadcrumb"
import { type ShowTableData, showColumns } from "@/components/Shows/columns"
import { isLoggedIn } from "@/hooks/useAuth"
import { usePlugin } from "@/hooks/useEntities"

export const Route = createFileRoute("/_layout/plugin/$pluginId_/shows")({
  component: PluginShowsPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Plugin Shows - Stream Channeler" }],
  }),
})

function PluginShowsPage() {
  const { pluginId } = Route.useParams()
  const { data: plugin } = usePlugin(pluginId)

  return (
    <DetailTablePage<ShowTableData>
      title={<DetailBreadcrumb plugin={plugin} trailing="Shows" />}
      columns={showColumns}
      queryKey={["plugins", pluginId, "shows"]}
      fetchTable={async (params) => {
        const result = await ShowsService.getPluginShows({
          pluginId,
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
      columnVisibilityKey="shows-column-visibility"
      emptyIcon={Clapperboard}
      emptyTitle="This plugin has no shows yet"
      emptyDescription="Shows will appear here once its sources have them"
    />
  )
}
