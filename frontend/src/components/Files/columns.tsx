// TODO: Validate
import type { ColumnDef } from "@tanstack/react-table"
import type { FileListPublic } from "@/client"
import {
  DateCell,
  ParentLinkCell,
  TruncatedCell,
} from "@/components/Common/TableCells"
import { extraText } from "@/lib/extra"
import { FileActionsMenu } from "./ActionsMenu"
import { FileContentCell } from "./ContentCell"

export type FileTableData = FileListPublic & { pending?: boolean }

export const fileColumns: ColumnDef<FileTableData>[] = [
  {
    accessorKey: "plugin_name",
    header: "Plugin",
    cell: ({ row }) => (
      <ParentLinkCell
        to="/sources"
        search={{ plugin_id: row.original.plugin_id }}
        name={row.original.plugin_name}
      />
    ),
  },
  {
    accessorKey: "key",
    header: "Key",
    cell: ({ row }) =>
      row.original.pending ? (
        <span className="font-medium text-muted-foreground block max-w-48 whitespace-normal wrap-break-word">
          {row.original.key}
        </span>
      ) : (
        <span className="font-medium block max-w-48 whitespace-normal wrap-break-word">
          {row.original.key}
        </span>
      ),
  },
  {
    id: "content",
    header: "Content",
    enableSorting: false,
    enableColumnFilter: false,
    cell: ({ row }) =>
      row.original.pending ? (
        <span className="text-muted-foreground text-sm">-</span>
      ) : (
        <FileContentCell fileId={row.original.id} fileName={row.original.key} />
      ),
  },
  {
    accessorKey: "data_timestamp",
    header: "Data Timestamp",
    meta: { filterVariant: "dateRange" },
    cell: ({ row }) => <DateCell value={row.original.data_timestamp} />,
  },
  {
    accessorKey: "update_at",
    header: "Update At",
    meta: { filterVariant: "dateRange" },
    cell: ({ row }) => <DateCell value={row.original.update_at} />,
  },
  {
    accessorKey: "deleted_at",
    header: "Deleted At",
    meta: { filterVariant: "dateRange" },
    cell: ({ row }) => <DateCell value={row.original.deleted_at} />,
  },
  {
    accessorKey: "extra",
    header: "Extra",
    cell: ({ row }) => <TruncatedCell value={extraText(row.original.extra)} />,
  },
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => <TruncatedCell value={row.original.id} />,
  },
  {
    id: "actions",
    enableSorting: false,
    enableColumnFilter: false,
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <div className="flex justify-end">
        {row.original.pending ? null : <FileActionsMenu file={row.original} />}
      </div>
    ),
  },
]
