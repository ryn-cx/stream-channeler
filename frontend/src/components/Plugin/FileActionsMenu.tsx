import { ActionsMenu } from "@/components/Common/ActionsMenu"
import DeleteFile from "./DeleteFile"
import EditFile from "./EditFile"
import type { FileTableData } from "./fileColumns"

interface FileActionsMenuProps {
  file: FileTableData
}

export const FileActionsMenu = ({ file }: FileActionsMenuProps) => {
  return (
    <ActionsMenu>
      <EditFile file={file} />
      <DeleteFile file={file} />
    </ActionsMenu>
  )
}
