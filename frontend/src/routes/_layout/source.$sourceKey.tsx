// TODO: Validate
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Tv } from "lucide-react"

import { ShowsService } from "@/client"
import {
  DetailTablePage,
  serializeTableQuery,
} from "@/components/Common/DataTable"
import AddShow from "@/components/Shows/Add"
import { type ShowTableData, showColumns } from "@/components/Shows/columns"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/source/$sourceKey")({
  component: SourceDetailPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Source Shows - Stream Channeler" }],
  }),
})

function SourceDetailPage() {
  const { sourceKey } = Route.useParams()

  return (
    <DetailTablePage<ShowTableData>
      title="Shows"
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
