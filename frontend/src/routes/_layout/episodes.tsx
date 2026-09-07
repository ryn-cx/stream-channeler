// TODO: Validate
import { createFileRoute } from "@tanstack/react-router"
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
import { requireSuperuser } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/episodes")({
  component: EpisodesPage,
  beforeLoad: requireSuperuser,
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
      defaultHidden={{
        key: false,
        canonical_episode_id: false,
        canonical_episode_ids: false,
        plugin_id: false,
        source_id: false,
        title_id: false,
        season_id: false,
        id: false,
      }}
      emptyIcon={Film}
      fetchTable={async (params) => {
        const result = await EpisodesService.getEpisodes({
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
        defaultHidden: {
          key: false,
          canonical_title_id: false,
          canonical_season_id: false,
          id: false,
        },
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
