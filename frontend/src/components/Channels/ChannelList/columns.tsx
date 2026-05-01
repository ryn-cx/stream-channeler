// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"

import type { ChannelOutput } from "@/client"
import { CopyId } from "@/components/Common/CopyId"
import { cn } from "@/lib/utils"
import { visibilityDotClass, visibilityLabel } from "@/lib/visibility"
import { ManageShowsButton } from "../ChannelDetail/AddUrlsToQueueButton"
import DeleteChannel from "./DeleteChannel"
import EditChannel from "./EditChannel"

export const columns: ColumnDef<ChannelOutput>[] = [
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => <CopyId id={row.original.id} />,
  },
  {
    accessorKey: "channel_number",
    header: "Ch#",
    cell: ({ row }) => (
      <span className="text-muted-foreground tabular-nums">
        {row.original.channel_number ?? "—"}
      </span>
    ),
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
    accessorFn: (row) => visibilityLabel(row.visibility),
    id: "visibility",
    header: "Visibility",
    cell: ({ row }) => {
      const visibility = row.original.visibility
      return (
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "size-2 rounded-full",
              visibilityDotClass(visibility),
            )}
          />
          <span
            className={visibility === "private" ? "text-muted-foreground" : ""}
          >
            {visibilityLabel(visibility)}
          </span>
        </div>
      )
    },
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
        <ManageShowsButton channelId={row.original.id} variant="icon" />
        <DeleteChannel id={row.original.id} />
      </div>
    ),
  },
]
