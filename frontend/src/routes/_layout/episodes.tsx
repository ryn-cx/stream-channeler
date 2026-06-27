import { createFileRoute, redirect } from "@tanstack/react-router"
import { Film } from "lucide-react"

import { EpisodesService } from "@/client"
import {
  type EpisodeTableData,
  episodeColumns,
} from "@/components/Episodes/columns"
import { MediaListPage } from "@/components/Media/MediaListPage"
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
