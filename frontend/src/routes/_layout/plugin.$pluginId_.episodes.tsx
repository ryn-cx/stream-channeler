// TODO: Validate
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Film } from "lucide-react"

import { EpisodesService } from "@/client"
import { BackButton } from "@/components/Common/BackButton"
import {
  DetailTablePage,
  serializeTableQuery,
} from "@/components/Common/DataTable"
import { DetailBreadcrumb } from "@/components/Common/DetailBreadcrumb"
import {
  type EpisodeTableData,
  episodeColumns,
} from "@/components/Episodes/columns"
import { isLoggedIn } from "@/hooks/useAuth"
import { usePlugin } from "@/hooks/useEntities"

export const Route = createFileRoute("/_layout/plugin/$pluginId_/episodes")({
  component: PluginEpisodesPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Plugin Episodes - Stream Channeler" }],
  }),
})

function PluginEpisodesPage() {
  const { pluginId } = Route.useParams()
  const { data: plugin } = usePlugin(pluginId)

  return (
    <DetailTablePage<EpisodeTableData>
      title={<DetailBreadcrumb plugin={plugin} trailing="Episodes" />}
      backButton={<BackButton to="/plugin/$pluginId" params={{ pluginId }} />}
      columns={episodeColumns}
      queryKey={["plugins", pluginId, "episodes"]}
      fetchTable={async (params) => {
        const result = await EpisodesService.getPluginEpisodes({
          pluginId,
          offset: params.offset,
          limit: params.limit,
          ...serializeTableQuery(params, episodeColumns),
        })
        return {
          data: result.data,
          total_count: result.total_count,
          filtered_count: result.filtered_count,
          is_server_side: result.is_server_side,
        }
      }}
      columnVisibilityKey="episodes-column-visibility"
      defaultHidden={{ key: false, id: false }}
      emptyIcon={Film}
      emptyTitle="This plugin has no episodes yet"
      emptyDescription="Episodes will appear here once its seasons have them"
    />
  )
}
