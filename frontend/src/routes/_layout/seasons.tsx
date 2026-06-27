import { createFileRoute, redirect } from "@tanstack/react-router"
import { Layers } from "lucide-react"

import { SeasonsService } from "@/client"
import { MediaListPage } from "@/components/Media/MediaListPage"
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
