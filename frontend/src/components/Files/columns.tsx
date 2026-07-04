// TODO: Validate
import type { ColumnDef } from "@tanstack/react-table"
import type { FilePublic } from "@/client"
import { DateCell, TruncatedCell } from "@/components/Common/TableCells"

import { FileActionsMenu } from "./ActionsMenu"
import { FileContentCell } from "./ContentCell"

export type FileTableData = FilePublic & { pending?: boolean }

export const fileColumns: ColumnDef<FileTableData>[] = [
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
  // The content column is just a button view the content so it has to use id instead of
  // accessorKey because there is nothing to access.
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
    cell: ({ row }) => <TruncatedCell value={row.original.extra} />,
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
