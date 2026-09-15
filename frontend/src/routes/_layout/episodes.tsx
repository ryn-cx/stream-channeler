// TODO: Validate
import { createFileRoute } from "@tanstack/react-router"
import { Film } from "lucide-react"

import { EpisodesService, TmdbEpisodesService } from "@/client"
import {
  MediaListPage,
  serializeTableQuery,
  validateMediaSearch,
} from "@/components/Common/DataTable"
import {
  type EpisodeTableData,
  episodeColumns,
} from "@/components/Episodes/columns"
import {
  type TmdbEpisodeTableData,
  tmdbEpisodeColumns,
} from "@/components/Episodes/tmdbColumns"
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
    <MediaListPage<EpisodeTableData, TmdbEpisodeTableData>
      title="Episodes"
      path="/episodes"
      columns={episodeColumns}
      columnVisibilityKey="episodes-column-visibility"
      defaultHidden={{
        key: false,
        tmdb_episode_id: false,
        tmdb_episode_ids: false,
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
      tmdb={{
        columns: tmdbEpisodeColumns,
        defaultHidden: {
          key: false,
          tmdb_title_id: false,
          tmdb_season_id: false,
          id: false,
        },
        fetchTable: async (params) => {
          const result = await TmdbEpisodesService.getTmdbEpisodes({
            offset: params.offset,
            limit: params.limit,
            ...serializeTableQuery(params, tmdbEpisodeColumns),
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
