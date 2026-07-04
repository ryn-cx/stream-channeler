// TODO: Validate
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Layers } from "lucide-react"

import { SeasonsService } from "@/client"
import { BackButton } from "@/components/Common/BackButton"
import {
  DetailTablePage,
  serializeTableQuery,
} from "@/components/Common/DataTable"
import { DetailBreadcrumb } from "@/components/Common/DetailBreadcrumb"
import {
  type SeasonTableData,
  seasonColumns,
} from "@/components/Seasons/columns"
import { isLoggedIn } from "@/hooks/useAuth"
import { usePlugin } from "@/hooks/useEntities"

export const Route = createFileRoute("/_layout/plugin/$pluginId_/seasons")({
  component: PluginSeasonsPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Plugin Seasons - Stream Channeler" }],
  }),
})

function PluginSeasonsPage() {
  const { pluginId } = Route.useParams()
  const { data: plugin } = usePlugin(pluginId)

  return (
    <DetailTablePage<SeasonTableData>
      title={<DetailBreadcrumb plugin={plugin} trailing="Seasons" />}
      backButton={<BackButton to="/plugin/$pluginId" params={{ pluginId }} />}
      columns={seasonColumns}
      queryKey={["plugins", pluginId, "seasons"]}
      fetchTable={async (params) => {
        const result = await SeasonsService.getPluginSeasons({
          pluginId,
          offset: params.offset,
          limit: params.limit,
          ...serializeTableQuery(params, seasonColumns),
        })
        return {
          data: result.data,
          total_count: result.total_count,
          filtered_count: result.filtered_count,
          is_server_side: result.is_server_side,
        }
      }}
      columnVisibilityKey="seasons-column-visibility"
      emptyIcon={Layers}
      emptyTitle="This plugin has no seasons yet"
      emptyDescription="Seasons will appear here once its shows have them"
    />
  )
}
