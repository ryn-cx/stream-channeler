// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"

import type { ChannelListOutput } from "@/client"
import { ChannelNumber } from "@/components/Channels/ChannelNumber"
import { cn } from "@/lib/utils"
import { visibilityDotClass, visibilityLabel } from "@/lib/visibility"
import { ChannelActions } from "./ChannelActions"

export const channelColumns: ColumnDef<ChannelListOutput>[] = [
  {
    id: "channel_number",
    accessorFn: (row) => row.channel_number,
    header: "Channel #",
    meta: { filterVariant: "range" },
    cell: ({ row }) => (
      <ChannelNumber channelNumber={row.original.channel_number} />
    ),
  },
  {
    id: "name",
    accessorFn: (row) => row.name ?? "Channel",
    header: "Name",
    cell: ({ row }) => (
      <Link
        to="/channels/$channelId"
        params={{ channelId: row.original.id }}
        className="font-medium hover:underline"
      >
        {row.original.name ?? "Channel"}
      </Link>
    ),
  },
  {
    id: "username",
    accessorFn: (row) => row.username ?? "Anonymous",
    header: "Owner",
    meta: { filterVariant: "select" },
    filterFn: "equalsString",
  },
  {
    accessorKey: "visibility",
    header: "Visibility",
    meta: { filterVariant: "select" },
    filterFn: "equalsString",
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "size-2 rounded-full",
            visibilityDotClass(row.original.visibility),
          )}
        />
        {visibilityLabel(row.original.visibility)}
      </div>
    ),
  },
  {
    accessorKey: "favorite_count",
    header: "Favorites",
    meta: { filterVariant: "range" },
    cell: ({ row }) => (
      <span className="tabular-nums">{row.original.favorite_count}</span>
    ),
  },
  {
    id: "anonymous",
    accessorFn: (row) => (row.anonymous ? "Yes" : "No"),
    header: "Anonymous",
    meta: { filterVariant: "select" },
    filterFn: "equalsString",
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.anonymous ? "Yes" : "No"}
      </span>
    ),
  },
  {
    id: "actions",
    enableSorting: false,
    enableColumnFilter: false,
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => <ChannelActions channel={row.original} />,
  },
]
