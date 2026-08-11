// TODO: Validate
import { createFileRoute, redirect } from "@tanstack/react-router"
import { FileText } from "lucide-react"

import { FilesService } from "@/client"
import { BackButton } from "@/components/Common/BackButton"
import {
  DetailTablePage,
  serializeTableQuery,
} from "@/components/Common/DataTable"
import { DetailBreadcrumb } from "@/components/Common/DetailBreadcrumb"
import AddFile from "@/components/Files/Add"
import { type FileTableData, fileColumns } from "@/components/Files/columns"
import { isLoggedIn } from "@/hooks/useAuth"
import { usePlugin } from "@/hooks/useEntities"

export const Route = createFileRoute("/_layout/plugin/$pluginId_/files")({
  component: PluginFilesPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Plugin Files - Stream Channeler" }],
  }),
})

// TODO: Validate
function PluginFilesPage() {
  const { pluginId } = Route.useParams()
  const { data: plugin } = usePlugin(pluginId)

  return (
    <DetailTablePage<FileTableData>
      title={<DetailBreadcrumb plugin={plugin} trailing="Files" />}
      backButton={<BackButton to="/plugin/$pluginId" params={{ pluginId }} />}
      columns={fileColumns}
      queryKey={["plugins", pluginId, "files"]}
      fetchTable={async (params) => {
        const result = await FilesService.getPluginFiles({
          pluginId,
          offset: params.offset,
          limit: params.limit,
          ...serializeTableQuery(params, fileColumns),
        })
        return {
          data: result.data,
          total_count: result.total_count,
          filtered_count: result.filtered_count,
          is_server_side: result.is_server_side,
        }
      }}
      columnVisibilityKey="files-column-visibility"
      defaultHidden={{ id: false }}
      emptyIcon={FileText}
      emptyTitle="This plugin has no files yet"
      emptyDescription="Add a file to get started"
      headerActions={<AddFile pluginId={pluginId} />}
    />
  )
}
