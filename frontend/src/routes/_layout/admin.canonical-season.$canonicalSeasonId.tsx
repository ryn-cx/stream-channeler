// TODO: Validate
import { createFileRoute } from "@tanstack/react-router"
import { Film } from "lucide-react"

import { CanonicalEpisodesService } from "@/client"
import {
  type CanonicalEpisodeTableData,
  canonicalEpisodeColumns,
} from "@/components/CanonicalEpisodes/columns"
import { BackButton } from "@/components/Common/BackButton"
import {
  DetailTablePage,
  serializeTableQuery,
} from "@/components/Common/DataTable"
import { DetailBreadcrumb } from "@/components/Common/DetailBreadcrumb"
import { useCanonicalSeason, useCanonicalShow } from "@/hooks/useEntities"

export const Route = createFileRoute(
  "/_layout/admin/canonical-season/$canonicalSeasonId",
)({
  component: CanonicalSeasonDetailPage,
  head: () => ({
    meta: [{ title: "Canonical Season Episodes - Stream Channeler" }],
  }),
})

// TODO: Validate
function CanonicalSeasonDetailPage() {
  const { canonicalSeasonId } = Route.useParams()
  const { data: canonicalSeason } = useCanonicalSeason(canonicalSeasonId)
  const { data: canonicalShow } = useCanonicalShow(
    canonicalSeason?.canonical_show_id,
  )

  return (
    <DetailTablePage<CanonicalEpisodeTableData>
      title={
        <DetailBreadcrumb
          canonicalShow={canonicalShow}
          canonicalSeason={canonicalSeason}
          trailing="Episodes"
          current="canonicalSeason"
        />
      }
      backButton={<BackButton to="/admin/canonical-seasons" />}
      columns={canonicalEpisodeColumns}
      queryKey={["canonical-seasons", canonicalSeasonId, "canonical-episodes"]}
      fetchTable={async (params) => {
        const result =
          await CanonicalEpisodesService.getCanonicalSeasonEpisodes({
            canonicalSeasonId,
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
      emptyTitle="This season has no episodes yet"
      emptyDescription="Episodes appear here once a copy of one has been imported"
    />
  )
}
