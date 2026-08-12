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
import { useCanonicalShow } from "@/hooks/useEntities"

export const Route = createFileRoute(
  "/_layout/admin/canonical-show/$canonicalShowId_/episodes",
)({
  component: CanonicalShowEpisodesPage,
  head: () => ({
    meta: [{ title: "Canonical Show Episodes - Stream Channeler" }],
  }),
})

// TODO: Validate
function CanonicalShowEpisodesPage() {
  const { canonicalShowId } = Route.useParams()
  const { data: canonicalShow } = useCanonicalShow(canonicalShowId)

  return (
    <DetailTablePage<CanonicalEpisodeTableData>
      title={
        <DetailBreadcrumb canonicalShow={canonicalShow} trailing="Episodes" />
      }
      backButton={
        <BackButton
          to="/admin/canonical-show/$canonicalShowId"
          params={{ canonicalShowId }}
        />
      }
      columns={canonicalEpisodeColumns}
      queryKey={["canonical-shows", canonicalShowId, "canonical-episodes"]}
      fetchTable={async (params) => {
        const result = await CanonicalEpisodesService.getCanonicalShowEpisodes({
          canonicalShowId,
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
      emptyTitle="This title has no episodes yet"
      emptyDescription="Episodes appear here once a copy of one has been imported"
    />
  )
}
