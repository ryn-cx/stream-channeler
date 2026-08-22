// TODO: Validate
import type { ColumnDef } from "@tanstack/react-table"

import type { UnmatchedSourceOutput } from "@/client"
import { DateCell } from "@/components/Common/TableCells"
import { UnmatchedSourceImportForm } from "./UnmatchedSourceImportForm"

export const unmatchedSourceColumns: ColumnDef<UnmatchedSourceOutput>[] = [
  {
    id: "show_name",
    accessorFn: (row) => row.show_name ?? "",
    header: "Show",
  },
  {
    id: "provider_name",
    accessorFn: (row) => row.provider_name,
    header: "Provider",
    meta: { filterVariant: "select" },
    filterFn: "equalsString",
  },
  {
    id: "plugin_key",
    accessorFn: (row) => row.plugin_key ?? "",
    header: "Plugin",
    meta: { filterVariant: "select" },
    filterFn: "equalsString",
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm">
        {row.original.plugin_key ?? "No plugin"}
      </span>
    ),
  },
  {
    id: "created_at",
    accessorFn: (row) => row.created_at,
    header: "Found",
    cell: ({ row }) => <DateCell value={row.original.created_at} />,
  },
  {
    id: "actions",
    header: "Import URL",
    enableSorting: false,
    cell: ({ row }) => (
      <UnmatchedSourceImportForm unmatchedSource={row.original} />
    ),
  },
]
