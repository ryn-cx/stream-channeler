import { createFileRoute, redirect } from "@tanstack/react-router"
import { Layers } from "lucide-react"

import { SeasonsService } from "@/client"
import { MediaListPage } from "@/components/Common/DataTable"
import {
  type SeasonTableData,
  seasonColumns,
} from "@/components/Seasons/columns"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/seasons")({
  component: SeasonsPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Seasons - Stream Channeler" }],
  }),
})

function SeasonsPage() {
  return (
    <MediaListPage<SeasonTableData>
      title="Seasons"
      columns={seasonColumns}
      columnVisibilityKey="seasons-column-visibility"
      defaultHidden={{ key: false, id: false }}
      emptyIcon={Layers}
      fetchTable={async (owner, params) => {
        const result = await SeasonsService.getSeasons({
          owner,
          offset: params.offset,
          limit: params.limit,
          sortOptions: JSON.stringify(params.sorting),
          filterOptions: JSON.stringify(params.columnFilters),
        })
        return {
          data: result.data,
          total_count: result.total_count,
          filtered_count: result.filtered_count,
          is_server_side: result.is_server_side,
        }
      }}
    />
  )
}
