// TODO: Validate
import type { ColumnDef } from "@tanstack/react-table"

import type { UserActionOutput } from "@/client"
import { DateCell } from "@/components/Common/TableCells"
import { Badge } from "@/components/ui/badge"

// TODO: Validate
export const userActionColumns: ColumnDef<UserActionOutput>[] = [
  {
    id: "created_at",
    accessorFn: (row) => row.created_at,
    header: "When",
    meta: { filterVariant: "dateRange", cellClassName: "align-top" },
    cell: ({ row }) => <DateCell value={row.original.created_at} />,
  },
  {
    id: "action",
    accessorFn: (row) => row.action,
    header: "Action",
    meta: { filterVariant: "select", cellClassName: "align-top" },
    filterFn: "equalsString",
    cell: ({ row }) => <Badge variant="outline">{row.original.action}</Badge>,
  },
  {
    id: "username",
    accessorFn: (row) => row.username ?? "",
    header: "User",
    meta: { cellClassName: "align-top" },
    cell: ({ row }) =>
      row.original.user_id ? (
        <span className="whitespace-normal wrap-break-word">
          {row.original.username ?? row.original.email}
        </span>
      ) : (
        <span className="text-muted-foreground">Anonymous</span>
      ),
  },
  {
    id: "email",
    accessorFn: (row) => row.email ?? "",
    header: "Email",
    meta: { cellClassName: "align-top" },
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm">
        {row.original.email ?? "-"}
      </span>
    ),
  },
  {
    id: "ip_address",
    accessorFn: (row) => row.ip_address ?? "",
    header: "IP Address",
    meta: { cellClassName: "align-top" },
    cell: ({ row }) => (
      <span className="font-mono text-sm">
        {row.original.ip_address ?? "-"}
      </span>
    ),
  },
  {
    id: "details",
    accessorFn: (row) => JSON.stringify(row.details),
    header: "Details",
    meta: { cellClassName: "align-top" },
    enableSorting: false,
    cell: ({ row }) => (
      <dl className="grid grid-cols-[auto_1fr] gap-x-2 text-xs">
        {Object.entries(row.original.details).map(([key, value]) => (
          <div key={key} className="contents">
            <dt className="text-muted-foreground">{key}</dt>
            <dd className="whitespace-normal break-all">
              {typeof value === "string" ? value : JSON.stringify(value)}
            </dd>
          </div>
        ))}
      </dl>
    ),
  },
]
