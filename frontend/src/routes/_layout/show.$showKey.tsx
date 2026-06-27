import { useQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Layers } from "lucide-react"

import { ShowsService } from "@/client"
import { DetailTablePage } from "@/components/Media/DetailTablePage"
import AddSeason from "@/components/Seasons/Add"
import {
  type SeasonTableData,
  seasonColumns,
} from "@/components/Seasons/columns"
import { isLoggedIn } from "@/hooks/useAuth"

function getSeasonsQueryOptions(showKey: string) {
  return {
    queryFn: () =>
      ShowsService.getSeasons({ showId: showKey }) as unknown as Promise<
        SeasonTableData[]
      >,
    queryKey: ["shows", showKey, "seasons"],
  }
}

export const Route = createFileRoute("/_layout/show/$showKey")({
  component: ShowDetailPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Show Seasons - Stream Channeler" }],
  }),
})

function ShowDetailPage() {
  const { showKey } = Route.useParams()
  const { data } = useQuery(getSeasonsQueryOptions(showKey))

  return (
    <DetailTablePage
      title="Seasons"
      columns={seasonColumns}
      data={data}
      columnVisibilityKey="seasons-column-visibility"
      emptyIcon={Layers}
      emptyTitle="This show has no seasons yet"
      emptyDescription="Add a season to get started"
      headerActions={<AddSeason showKey={showKey} />}
    />
  )
}
