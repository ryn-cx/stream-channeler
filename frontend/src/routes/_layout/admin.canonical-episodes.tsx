// TODO: Validate
import { createFileRoute } from "@tanstack/react-router"
import { Film } from "lucide-react"

import { CanonicalEpisodesService } from "@/client"
import {
  type CanonicalEpisodeTableData,
  canonicalEpisodeColumns,
} from "@/components/CanonicalEpisodes/columns"
import {
  DetailTablePage,
  serializeTableQuery,
} from "@/components/Common/DataTable"

export const Route = createFileRoute("/_layout/admin/canonical-episodes")({
  component: CanonicalEpisodesPage,
  head: () => ({
    meta: [{ title: "Canonical Episodes - Stream Channeler" }],
  }),
})

// TODO: Validate
function CanonicalEpisodesPage() {
  return (
    <DetailTablePage<CanonicalEpisodeTableData>
      title="Canonical Episodes"
      columns={canonicalEpisodeColumns}
      queryKey={["canonical-episodes"]}
      fetchTable={async (params) => {
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
      }}
      columnVisibilityKey="canonical-episodes-column-visibility"
      defaultHidden={{ key: false, id: false }}
      emptyIcon={Film}
      emptyTitle="There are no canonical episodes yet"
      emptyDescription="An episode appears here once a copy of it has been imported"
    />
  )
}
