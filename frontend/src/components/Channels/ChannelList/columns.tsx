// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"

import type { ChannelOutput } from "@/client"
import { CopyId } from "@/components/Common/CopyId"
import { cn } from "@/lib/utils"
import DeleteChannel from "./DeleteChannel"
import EditChannel from "./EditChannel"

export const columns: ColumnDef<ChannelOutput>[] = [
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => <CopyId id={row.original.id} />,
  },
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => {
      let searchParams = {}
      if (row.original.default_order) {
        searchParams = JSON.parse(row.original.default_order)
      }

      return (
        <Link
          to="/channels/$channelId"
          params={{ channelId: row.original.id }}
          search={searchParams}
          className="hover:underline text-primary"
        >
          {row.original.name}
        </Link>
      )
    },
    meta: {
      filterVariant: "text",
    },
  },
  {
    accessorFn: (row) => (row.public ? "Public" : "Private"),
    id: "public",
    header: "Visibility",
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "size-2 rounded-full",
            row.original.public ? "bg-green-500" : "bg-gray-400",
          )}
        />
        <span className={row.original.public ? "" : "text-muted-foreground"}>
          {row.original.public ? "Public" : "Private"}
        </span>
      </div>
    ),
  },
  {
    accessorKey: "default_order",
    header: "Default Order",
    cell: ({ row }) => {
      const defaultOrder = row.original.default_order
      let displayText = "None"

      if (defaultOrder) {
        try {
          const parsed = JSON.parse(defaultOrder)
          displayText = JSON.stringify(parsed, null, 2)
        } catch {
          displayText = defaultOrder
        }
      }

      return (
        <div className="w-full max-w-[300px]">
          <pre className={cn(!defaultOrder && "italic")}>{displayText}</pre>
        </div>
      )
    },
    meta: {
      filterVariant: "text",
    },
  },
  {
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <div className="flex justify-end">
        <EditChannel channel={row.original} />
        <DeleteChannel id={row.original.id} />
      </div>
    ),
  },
]
