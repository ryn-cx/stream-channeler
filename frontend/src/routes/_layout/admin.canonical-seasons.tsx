// TODO: Validate
import { createFileRoute } from "@tanstack/react-router"
import { Layers } from "lucide-react"

import { CanonicalSeasonsService } from "@/client"
import {
  type CanonicalSeasonTableData,
  canonicalSeasonColumns,
} from "@/components/CanonicalSeasons/columns"
import {
  DetailTablePage,
  serializeTableQuery,
} from "@/components/Common/DataTable"

export const Route = createFileRoute("/_layout/admin/canonical-seasons")({
  component: CanonicalSeasonsPage,
  head: () => ({
    meta: [{ title: "Canonical Seasons - Stream Channeler" }],
  }),
})

// TODO: Validate
function CanonicalSeasonsPage() {
  return (
    <DetailTablePage<CanonicalSeasonTableData>
      title="Canonical Seasons"
      columns={canonicalSeasonColumns}
      queryKey={["canonical-seasons"]}
      fetchTable={async (params) => {
        const result = await CanonicalSeasonsService.getCanonicalSeasons({
          offset: params.offset,
          limit: params.limit,
          ...serializeTableQuery(params, canonicalSeasonColumns),
        })
        return {
          data: result.data,
          total_count: result.total_count,
          filtered_count: result.filtered_count,
          is_server_side: result.is_server_side,
        }
      }}
      columnVisibilityKey="canonical-seasons-column-visibility"
      defaultHidden={{ id: false }}
      emptyIcon={Layers}
      emptyTitle="There are no canonical seasons yet"
      emptyDescription="A season appears here once a copy of it has been imported"
    />
  )
}
