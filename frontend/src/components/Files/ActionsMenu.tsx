// TODO: Validate
import { ActionsMenu } from "@/components/Common/ActionsMenu"
import type { FileTableData } from "./columns"
import DeleteFile from "./Delete"
import EditFile from "./Edit"

interface FileActionsMenuProps {
  file: FileTableData
}

// TODO: Validate
export const FileActionsMenu = ({ file }: FileActionsMenuProps) => {
  return (
    <ActionsMenu>
      <EditFile file={file} />
      <DeleteFile file={file} />
    </ActionsMenu>
  )
}
