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
import { usePlugin, useShow, useSource } from "@/hooks/useEntities"

export const Route = createFileRoute("/_layout/show/$showKey_/episodes")({
  component: ShowEpisodesPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Show Episodes - Stream Channeler" }],
  }),
})

function ShowEpisodesPage() {
  const { showKey } = Route.useParams()
  const { data: show } = useShow(showKey)
  const { data: source } = useSource(show?.source_id)
  const { data: plugin } = usePlugin(source?.plugin_id)

  return (
    <DetailTablePage<EpisodeTableData>
      title={
        <DetailBreadcrumb
          plugin={plugin}
          source={source}
          show={show}
          trailing="Episodes"
        />
      }
      backButton={<BackButton to="/show/$showKey" params={{ showKey }} />}
      columns={episodeColumns}
      queryKey={["shows", showKey, "episodes"]}
      fetchTable={async (params) => {
        const result = await EpisodesService.getShowEpisodes({
          showId: showKey,
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
      emptyTitle="This show has no episodes yet"
      emptyDescription="Episodes will appear here once its seasons have them"
    />
  )
}
