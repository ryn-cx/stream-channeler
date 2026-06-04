import type { ColumnDef } from "@tanstack/react-table"

import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { UserTableData } from "./types"
import { UserActionsMenu } from "./UserActionsMenu"

export const columns: ColumnDef<UserTableData>[] = [
  {
    accessorKey: "full_name",
    header: "Full Name",
    cell: ({ row }) => {
      const fullName = row.original.full_name
      return (
        <div className="flex items-center gap-2">
          <span
            className={cn("font-medium", !fullName && "text-muted-foreground")}
          >
            {fullName || "N/A"}
          </span>
          {row.original.isCurrentUser && (
            <Badge variant="outline" className="text-xs">
              You
            </Badge>
          )}
        </div>
      )
    },
  },
  {
    accessorKey: "email",
    header: "Email",
    cell: ({ row }) => (
      <span className="text-muted-foreground">{row.original.email}</span>
    ),
  },
  {
    id: "is_superuser",
    accessorFn: (row) => (row.is_superuser ? "Superuser" : "User"),
    header: "Role",
    meta: { filterVariant: "select" },
    filterFn: "equalsString",
    cell: ({ row }) =>
      row.original.pending ? (
        <span className="text-muted-foreground">
          {row.original.is_superuser ? "Superuser" : "User"}
        </span>
      ) : (
        <Badge variant={row.original.is_superuser ? "default" : "secondary"}>
          {row.original.is_superuser ? "Superuser" : "User"}
        </Badge>
      ),
  },
  {
    id: "is_active",
    accessorFn: (row) => (row.is_active ? "Active" : "Inactive"),
    header: "Status",
    meta: { filterVariant: "select" },
    filterFn: "equalsString",
    cell: ({ row }) =>
      row.original.pending ? (
        <span className="text-muted-foreground">
          {row.original.is_active ? "Active" : "Inactive"}
        </span>
      ) : (
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "size-2 rounded-full",
              row.original.is_active ? "bg-green-500" : "bg-gray-400",
            )}
          />
          <span
            className={row.original.is_active ? "" : "text-muted-foreground"}
          >
            {row.original.is_active ? "Active" : "Inactive"}
          </span>
        </div>
      ),
  },
  {
    id: "actions",
    enableSorting: false,
    enableColumnFilter: false,
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <div className="flex justify-end">
        {row.original.pending ? null : <UserActionsMenu user={row.original} />}
      </div>
    ),
  },
]
