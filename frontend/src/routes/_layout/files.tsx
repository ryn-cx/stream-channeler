// TODO: Validate
import { createFileRoute } from "@tanstack/react-router"
import { FileText } from "lucide-react"

import { FilesService } from "@/client"
import {
  MediaListPage,
  serializeTableQuery,
  validateMediaSearch,
} from "@/components/Common/DataTable"
import { type FileTableData, fileColumns } from "@/components/Files/columns"
import { requireSuperuser } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/files")({
  component: AllFilesPage,
  beforeLoad: requireSuperuser,
  validateSearch: validateMediaSearch,
  head: () => ({
    meta: [{ title: "Files - Stream Channeler" }],
  }),
})

// TODO: Validate
function AllFilesPage() {
  return (
    <MediaListPage<FileTableData>
      title="Files"
      path="/files"
      columns={fileColumns}
      columnVisibilityKey="files-column-visibility"
      defaultHidden={{ id: false }}
      emptyIcon={FileText}
      fetchTable={async (scope, params) => {
        const result = await FilesService.getFiles({
          scope,
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
    />
  )
}
