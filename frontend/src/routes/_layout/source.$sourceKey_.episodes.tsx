// TODO: Validate
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Film } from "lucide-react"

import { EpisodesService } from "@/client"
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
import { usePlugin, useSource } from "@/hooks/useEntities"

export const Route = createFileRoute("/_layout/source/$sourceKey_/episodes")({
  component: SourceEpisodesPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Source Episodes - Stream Channeler" }],
  }),
})

function SourceEpisodesPage() {
  const { sourceKey } = Route.useParams()
  const { data: source } = useSource(sourceKey)
  const { data: plugin } = usePlugin(source?.plugin_id)

  return (
    <DetailTablePage<EpisodeTableData>
      title={
        <DetailBreadcrumb plugin={plugin} source={source} trailing="Episodes" />
      }
      columns={episodeColumns}
      queryKey={["sources", sourceKey, "episodes"]}
      fetchTable={async (params) => {
        const result = await EpisodesService.getSourceEpisodes({
          sourceId: sourceKey,
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
      emptyTitle="This source has no episodes yet"
      emptyDescription="Episodes will appear here once its seasons have them"
    />
  )
}
