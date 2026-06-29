import { createFileRoute, redirect } from "@tanstack/react-router"
import { Film } from "lucide-react"

import { EpisodesService } from "@/client"
import {
  type EpisodeTableData,
  episodeColumns,
} from "@/components/Episodes/columns"
import { MediaListPage } from "@/components/Common/DataTable"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/episodes")({
  component: EpisodesPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Episodes - Stream Channeler" }],
  }),
})

function EpisodesPage() {
  return (
    <MediaListPage<EpisodeTableData>
      title="Episodes"
      columns={episodeColumns}
      columnVisibilityKey="episodes-column-visibility"
      defaultHidden={{ key: false, id: false }}
      emptyIcon={Film}
      fetchTable={async (owner, params) => {
        const result = await EpisodesService.getEpisodes({
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
