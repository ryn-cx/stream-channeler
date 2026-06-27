import { createFileRoute, redirect } from "@tanstack/react-router"
import { Database } from "lucide-react"

import { SourcesService } from "@/client"
import { MediaListPage } from "@/components/Media/MediaListPage"
import {
  type SourceTableData,
  sourceColumns,
} from "@/components/Sources/columns"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/sources")({
  component: SourcesPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Sources - Stream Channeler" }],
  }),
})

function SourcesPage() {
  return (
    <MediaListPage<SourceTableData>
      title="Sources"
      columns={sourceColumns}
      columnVisibilityKey="sources-column-visibility"
      defaultHidden={{ key: false, id: false }}
      emptyIcon={Database}
      fetchTable={async (owner, params) => {
        const result = await SourcesService.getSources({
          owner,
          offset: params.offset,
          limit: params.limit,
          sorting: JSON.stringify(params.sorting),
          filters: JSON.stringify(params.columnFilters),
        })
        return {
          data: result.data,
          count: result.count,
          server_side: result.server_side,
        }
      }}
    />
  )
}
