import { createFileRoute, redirect } from "@tanstack/react-router"
import { Clapperboard } from "lucide-react"

import { ShowsService } from "@/client"
import { MediaListPage } from "@/components/Media/MediaListPage"
import { type ShowTableData, showColumns } from "@/components/Shows/columns"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/shows")({
  component: ShowsPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Shows - Stream Channeler" }],
  }),
})

function ShowsPage() {
  return (
    <MediaListPage<ShowTableData>
      title="Shows"
      columns={showColumns}
      columnVisibilityKey="shows-column-visibility"
      defaultHidden={{ key: false, id: false }}
      emptyIcon={Clapperboard}
      fetchTable={async (owner, params) => {
        const result = await ShowsService.getShows({
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
