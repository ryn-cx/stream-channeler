// TODO: Validate
import { createFileRoute } from "@tanstack/react-router"
import { Tv } from "lucide-react"

import { ShowsService } from "@/client"
import {
  DetailTablePage,
  serializeTableQuery,
} from "@/components/Common/DataTable"
import { DetailBreadcrumb } from "@/components/Common/DetailBreadcrumb"
import AddShow from "@/components/Shows/Add"
import { type ShowTableData, showColumns } from "@/components/Shows/columns"
import { requireSuperuser } from "@/hooks/useAuth"
import { usePlugin, useSource } from "@/hooks/useEntities"

export const Route = createFileRoute("/_layout/source/$sourceKey")({
  component: SourceDetailPage,
  beforeLoad: requireSuperuser,
  head: () => ({
    meta: [{ title: "Source Shows - Stream Channeler" }],
  }),
})

// TODO: Validate
function SourceDetailPage() {
  const { sourceKey } = Route.useParams()
  const { data: source } = useSource(sourceKey)
  const { data: plugin } = usePlugin(source?.plugin_id)

  return (
    <DetailTablePage<ShowTableData>
      title={
        <DetailBreadcrumb
          plugin={plugin}
          source={source}
          trailing="Shows"
          current="source"
        />
      }
      columns={showColumns}
      queryKey={["sources", sourceKey, "shows"]}
      fetchTable={async (params) => {
        const result = await ShowsService.getSourceShows({
          sourceId: sourceKey,
          offset: params.offset,
          limit: params.limit,
          ...serializeTableQuery(params, showColumns),
        })
        return {
          data: result.data,
          total_count: result.total_count,
          filtered_count: result.filtered_count,
          is_server_side: result.is_server_side,
        }
      }}
      columnVisibilityKey="shows-column-visibility"
      emptyIcon={Tv}
      emptyTitle="This source has no shows yet"
      emptyDescription="Add a show to get started"
      headerActions={<AddShow sourceKey={sourceKey} />}
    />
  )
}
