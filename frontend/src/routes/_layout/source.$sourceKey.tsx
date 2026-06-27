import { useQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Tv } from "lucide-react"

import { SourcesService } from "@/client"
import { DetailTablePage } from "@/components/Media/DetailTablePage"
import AddShow from "@/components/Shows/Add"
import { type ShowTableData, showColumns } from "@/components/Shows/columns"
import { isLoggedIn } from "@/hooks/useAuth"

function getShowsQueryOptions(sourceKey: string) {
  return {
    queryFn: () =>
      SourcesService.getShows({ sourceId: sourceKey }) as unknown as Promise<
        ShowTableData[]
      >,
    queryKey: ["sources", sourceKey, "shows"],
  }
}

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
  const { data } = useQuery(getShowsQueryOptions(sourceKey))

  return (
    <DetailTablePage
      title="Shows"
      columns={showColumns}
      data={data}
      columnVisibilityKey="shows-column-visibility"
      emptyIcon={Tv}
      emptyTitle="This source has no shows yet"
      emptyDescription="Add a show to get started"
      headerActions={<AddShow sourceKey={sourceKey} />}
    />
  )
}
