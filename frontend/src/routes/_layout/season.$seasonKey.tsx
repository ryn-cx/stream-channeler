import { useQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Film } from "lucide-react"

import { SeasonsService } from "@/client"
import AddEpisode from "@/components/Episodes/Add"
import {
  type EpisodeTableData,
  episodeColumns,
} from "@/components/Episodes/columns"
import { DetailTablePage } from "@/components/Media/DetailTablePage"
import { isLoggedIn } from "@/hooks/useAuth"

function getEpisodesQueryOptions(seasonKey: string) {
  return {
    queryFn: () =>
      SeasonsService.getEpisodes({ seasonId: seasonKey }) as unknown as Promise<
        EpisodeTableData[]
      >,
    queryKey: ["seasons", seasonKey, "episodes"],
  }
}

export const Route = createFileRoute("/_layout/season/$seasonKey")({
  component: SeasonDetailPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Season Episodes - Stream Channeler" }],
  }),
})

function SeasonDetailPage() {
  const { seasonKey } = Route.useParams()
  const { data } = useQuery(getEpisodesQueryOptions(seasonKey))

  return (
    <DetailTablePage
      title="Episodes"
      columns={episodeColumns}
      data={data}
      columnVisibilityKey="episodes-column-visibility"
      emptyIcon={Film}
      emptyTitle="This season has no episodes yet"
      emptyDescription="Add an episode to get started"
      headerActions={<AddEpisode seasonKey={seasonKey} />}
    />
  )
}
