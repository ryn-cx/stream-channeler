// TODO: Validate
import { createFileRoute } from "@tanstack/react-router"
import { Layers } from "lucide-react"

import { SeasonsService } from "@/client"
import { BackButton } from "@/components/Common/BackButton"
import {
  DetailTablePage,
  serializeTableQuery,
} from "@/components/Common/DataTable"
import { DetailBreadcrumb } from "@/components/Common/DetailBreadcrumb"
import {
  type SeasonTableData,
  seasonColumns,
} from "@/components/Seasons/columns"
import { requireSuperuser } from "@/hooks/useAuth"
import { usePlugin, useSource } from "@/hooks/useEntities"

export const Route = createFileRoute("/_layout/source/$sourceKey_/seasons")({
  component: SourceSeasonsPage,
  beforeLoad: requireSuperuser,
  head: () => ({
    meta: [{ title: "Source Seasons - Stream Channeler" }],
  }),
})

// TODO: Validate
function SourceSeasonsPage() {
  const { sourceKey } = Route.useParams()
  const { data: source } = useSource(sourceKey)
  const { data: plugin } = usePlugin(source?.plugin_id)

  return (
    <DetailTablePage<SeasonTableData>
      title={
        <DetailBreadcrumb plugin={plugin} source={source} trailing="Seasons" />
      }
      backButton={<BackButton to="/source/$sourceKey" params={{ sourceKey }} />}
      columns={seasonColumns}
      queryKey={["sources", sourceKey, "seasons"]}
      fetchTable={async (params) => {
        const result = await SeasonsService.getSourceSeasons({
          sourceId: sourceKey,
          offset: params.offset,
          limit: params.limit,
          ...serializeTableQuery(params, seasonColumns),
        })
        return {
          data: result.data,
          total_count: result.total_count,
          filtered_count: result.filtered_count,
          is_server_side: result.is_server_side,
        }
      }}
      columnVisibilityKey="seasons-column-visibility"
      emptyIcon={Layers}
      emptyTitle="This source has no seasons yet"
      emptyDescription="Seasons will appear here once its shows have them"
    />
  )
}
