import { useQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Database } from "lucide-react"

import { PluginsService } from "@/client"
import { DetailTablePage } from "@/components/Media/DetailTablePage"
import AddSource from "@/components/Sources/Add"
import {
  type SourceTableData,
  sourceColumns,
} from "@/components/Sources/columns"
import { isLoggedIn } from "@/hooks/useAuth"

function getSourcesQueryOptions(pluginId: string) {
  return {
    queryFn: () =>
      PluginsService.getPluginSources({ pluginId }) as unknown as Promise<
        SourceTableData[]
      >,
    queryKey: ["plugins", pluginId, "sources"],
  }
}

export const Route = createFileRoute("/_layout/plugin/$pluginId")({
  component: PluginDetailPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Plugin Sources - Stream Channeler" }],
  }),
})

function PluginDetailPage() {
  const { pluginId } = Route.useParams()
  const { data } = useQuery(getSourcesQueryOptions(pluginId))

  return (
    <DetailTablePage
      title="Sources"
      columns={sourceColumns}
      data={data}
      columnVisibilityKey="sources-column-visibility"
      emptyIcon={Database}
      emptyTitle="This plugin has no sources yet"
      emptyDescription="Add a source to get started"
      headerActions={<AddSource pluginId={pluginId} />}
    />
  )
}
