// TODO: Validate
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Film } from "lucide-react"

import { EpisodesService } from "@/client"
import {
  MediaListPage,
  serializeTableQuery,
  validateMediaSearch,
} from "@/components/Common/DataTable"
import {
  type EpisodeTableData,
  episodeColumns,
} from "@/components/Episodes/columns"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/episodes")({
  component: EpisodesPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  validateSearch: validateMediaSearch,
  head: () => ({
    meta: [{ title: "Episodes - Stream Channeler" }],
  }),
})

function EpisodesPage() {
  return (
    <MediaListPage<EpisodeTableData>
      title="Episodes"
      path="/episodes"
      columns={episodeColumns}
      columnVisibilityKey="episodes-column-visibility"
      defaultHidden={{ key: false, id: false }}
      emptyIcon={Film}
      fetchTable={async (scope, params) => {
        const result = await EpisodesService.getEpisodes({
          scope,
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
    />
  )
}
