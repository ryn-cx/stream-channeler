// TODO: Validate
import { createFileRoute } from "@tanstack/react-router"
import { Clapperboard } from "lucide-react"

import { CanonicalTitlesService, TitlesService } from "@/client"
import {
  MediaListPage,
  serializeTableQuery,
  validateMediaSearch,
} from "@/components/Common/DataTable"
import {
  type CanonicalTitleTableData,
  canonicalTitleColumns,
} from "@/components/Titles/canonicalColumns"
import { type TitleTableData, titleColumns } from "@/components/Titles/columns"
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
    <MediaListPage<TitleTableData, CanonicalTitleTableData>
      title="Titles"
      path="/titles"
      columns={titleColumns}
      columnVisibilityKey="titles-column-visibility"
      defaultHidden={{
        key: false,
        canonical_title_id: false,
        canonical_title_ids: false,
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
      canonical={{
        columns: canonicalTitleColumns,
        defaultHidden: { id: false },
        fetchTable: async (params) => {
          const result = await CanonicalTitlesService.getCanonicalTitles({
            offset: params.offset,
            limit: params.limit,
            ...serializeTableQuery(params, canonicalTitleColumns),
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
