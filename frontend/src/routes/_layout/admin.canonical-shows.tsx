// TODO: Validate
import { createFileRoute } from "@tanstack/react-router"
import { Clapperboard } from "lucide-react"

import { CanonicalShowsService } from "@/client"
import {
  type CanonicalShowTableData,
  canonicalShowColumns,
} from "@/components/CanonicalShows/columns"
import {
  DetailTablePage,
  serializeTableQuery,
} from "@/components/Common/DataTable"

export const Route = createFileRoute("/_layout/admin/canonical-shows")({
  component: CanonicalShowsPage,
  head: () => ({
    meta: [{ title: "Canonical Shows - Stream Channeler" }],
  }),
})

// TODO: Validate
function CanonicalShowsPage() {
  return (
    <DetailTablePage<CanonicalShowTableData>
      title="Canonical Shows"
      columns={canonicalShowColumns}
      queryKey={["canonical-shows"]}
      fetchTable={async (params) => {
        const result = await CanonicalShowsService.getCanonicalShows({
          offset: params.offset,
          limit: params.limit,
          ...serializeTableQuery(params, canonicalShowColumns),
        })
        return {
          data: result.data,
          total_count: result.total_count,
          filtered_count: result.filtered_count,
          is_server_side: result.is_server_side,
        }
      }}
      columnVisibilityKey="canonical-shows-column-visibility"
      defaultHidden={{ id: false }}
      emptyIcon={Clapperboard}
      emptyTitle="There are no canonical titles yet"
      emptyDescription="A title appears here once a copy of it has been imported"
    />
  )
}
