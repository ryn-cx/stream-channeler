// TODO: Validate
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Film } from "lucide-react"

import { CanonicalEpisodesService, EpisodesService } from "@/client"
import {
  MediaListPage,
  serializeTableQuery,
  validateMediaSearch,
} from "@/components/Common/DataTable"
import {
  type CanonicalEpisodeTableData,
  canonicalEpisodeColumns,
} from "@/components/Episodes/canonicalColumns"
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

// TODO: Validate
function EpisodesPage() {
  return (
    <MediaListPage<EpisodeTableData, CanonicalEpisodeTableData>
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
      canonical={{
        columns: canonicalEpisodeColumns,
        defaultHidden: { key: false, id: false },
        fetchTable: async (params) => {
          const result = await CanonicalEpisodesService.getCanonicalEpisodes({
            offset: params.offset,
            limit: params.limit,
            ...serializeTableQuery(params, canonicalEpisodeColumns),
          })
          return {
            data: result.data,
            total_count: result.total_count,
            filtered_count: result.filtered_count,
            is_server_side: result.is_server_side,
          }
        },
      }}
    />
  )
}
