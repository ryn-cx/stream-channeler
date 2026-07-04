import { createFileRoute, redirect } from "@tanstack/react-router"
import { FileText } from "lucide-react"

import { FilesService } from "@/client"
import {
  MediaListPage,
  serializeTableQuery,
} from "@/components/Common/DataTable"
import { type FileTableData, fileColumns } from "@/components/Files/columns"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/files")({
  component: AllFilesPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Files - Stream Channeler" }],
  }),
})

function AllFilesPage() {
  return (
    <MediaListPage<FileTableData>
      title="Files"
      columns={fileColumns}
      columnVisibilityKey="files-column-visibility"
      defaultHidden={{ id: false }}
      emptyIcon={FileText}
      fetchTable={async (owner, params) => {
        const result = await FilesService.getFiles({
          owner,
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
