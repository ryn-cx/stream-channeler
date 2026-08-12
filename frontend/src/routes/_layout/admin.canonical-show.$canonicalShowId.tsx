// TODO: Validate
import { createFileRoute } from "@tanstack/react-router"
import { Layers } from "lucide-react"

import { CanonicalSeasonsService } from "@/client"
import {
  type CanonicalSeasonTableData,
  canonicalSeasonColumns,
} from "@/components/CanonicalSeasons/columns"
import { BackButton } from "@/components/Common/BackButton"
import {
  DetailTablePage,
  serializeTableQuery,
} from "@/components/Common/DataTable"
import { DetailBreadcrumb } from "@/components/Common/DetailBreadcrumb"
import { useCanonicalShow } from "@/hooks/useEntities"

export const Route = createFileRoute(
  "/_layout/admin/canonical-show/$canonicalShowId",
)({
  component: CanonicalShowDetailPage,
  head: () => ({
    meta: [{ title: "Canonical Show Seasons - Stream Channeler" }],
  }),
})

// TODO: Validate
function CanonicalShowDetailPage() {
  const { canonicalShowId } = Route.useParams()
  const { data: canonicalShow } = useCanonicalShow(canonicalShowId)

  return (
    <DetailTablePage<CanonicalSeasonTableData>
      title={
        <DetailBreadcrumb
          canonicalShow={canonicalShow}
          trailing="Seasons"
          current="canonicalShow"
        />
      }
      backButton={<BackButton to="/admin/canonical-shows" />}
      columns={canonicalSeasonColumns}
      queryKey={["canonical-shows", canonicalShowId, "canonical-seasons"]}
      fetchTable={async (params) => {
        const result = await CanonicalSeasonsService.getCanonicalShowSeasons({
          canonicalShowId,
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
      emptyTitle="This title has no seasons yet"
      emptyDescription="Seasons appear here once a copy of one has been imported"
    />
  )
}
