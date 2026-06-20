// TODO: Validate
import type { ColumnDef } from "@tanstack/react-table"
import { DateCell, TruncatedCell } from "@/components/Common/TableCells"

import { FileActionsMenu } from "./FileActionsMenu"
import { FileContentCell } from "./FileContentCell"

export interface FileTableData {
  key: string
  id: string
  plugin_id: string
  data_timestamp: string | null
  update_at: string | null
  deleted_at: string | null
  extra: string | null
  pending?: boolean
}

interface ContentServerFilter {
  value: string
  onChange: (value: string) => void
}

export function createFileColumns(
  contentFilter: ContentServerFilter,
): ColumnDef<FileTableData>[] {
  return [
    {
      accessorKey: "key",
      header: "Key",
      cell: ({ row }) =>
        row.original.pending ? (
          <span className="font-medium text-muted-foreground">
            {row.original.key}
          </span>
        ) : (
          <span className="font-medium">{row.original.key}</span>
        ),
    },
    {
      accessorKey: "content",
      header: "Content",
      enableSorting: false,
      meta: {
        serverFilter: {
          value: contentFilter.value,
          onChange: contentFilter.onChange,
          placeholder: "Search content...",
        },
      },
      cell: ({ row }) =>
        row.original.pending ? (
          <span className="text-muted-foreground text-sm">-</span>
        ) : (
          <FileContentCell fileId={row.original.id} />
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
          {row.original.pending ? null : (
            <FileActionsMenu file={row.original} />
          )}
        </div>
      ),
    },
  ]
}
