// TODO: Validate
import { createFileRoute } from "@tanstack/react-router"
import { Clapperboard } from "lucide-react"

import { TitlesService, TmdbTitlesService } from "@/client"
import {
  MediaListPage,
  serializeTableQuery,
  validateMediaSearch,
} from "@/components/Common/DataTable"
import { type TitleTableData, titleColumns } from "@/components/Titles/columns"
import {
  type TmdbTitleTableData,
  tmdbTitleColumns,
} from "@/components/Titles/tmdbColumns"
import { requireSuperuser } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/titles")({
  component: TitlesPage,
  beforeLoad: requireSuperuser,
  validateSearch: validateMediaSearch,
  head: () => ({
    meta: [{ title: "Titles - Stream Channeler" }],
  }),
})

// TODO: Validate
function TitlesPage() {
  return (
    <MediaListPage<TitleTableData, TmdbTitleTableData>
      title="Titles"
      path="/titles"
      columns={titleColumns}
      columnVisibilityKey="titles-column-visibility"
      defaultHidden={{
        key: false,
        tmdb_title_id: false,
        tmdb_title_ids: false,
        plugin_id: false,
        source_id: false,
        id: false,
      }}
      emptyIcon={Clapperboard}
      fetchTable={async (params) => {
        const result = await TitlesService.getTitles({
          offset: params.offset,
          limit: params.limit,
          ...serializeTableQuery(params, titleColumns),
        })
        return {
          data: result.data,
          total_count: result.total_count,
          filtered_count: result.filtered_count,
          is_server_side: result.is_server_side,
        }
      }}
      tmdb={{
        columns: tmdbTitleColumns,
        defaultHidden: { id: false },
        fetchTable: async (params) => {
          const result = await TmdbTitlesService.getTmdbTitles({
            offset: params.offset,
            limit: params.limit,
            ...serializeTableQuery(params, tmdbTitleColumns),
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
