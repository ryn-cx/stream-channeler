// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"

import type { ChannelQueueAdminOutput } from "@/client"
import { ChannelNumber } from "@/components/Channels/ChannelNumber"
import { DateCell } from "@/components/Common/TableCells"
import { ChannelQueueActions } from "./ChannelQueueActions"

export const channelQueueColumns: ColumnDef<ChannelQueueAdminOutput>[] = [
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
    id: "channel_name",
    accessorFn: (row) => row.channel_name ?? "Channel",
    header: "Channel",
    cell: ({ row }) => (
      <Link
        to="/channels/$channelId"
        params={{ channelId: row.original.channel_id }}
        className="font-medium hover:underline"
      >
        {row.original.channel_name ?? "Channel"}
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
    accessorKey: "url",
    header: "URL",
    cell: ({ row }) => (
      <a
        href={row.original.url}
        target="_blank"
        rel="noreferrer"
        className="hover:underline"
        title={row.original.url}
      >
        <span className="block max-w-xs truncate">{row.original.url}</span>
      </a>
    ),
  },
  {
    accessorKey: "status",
    header: "Status",
    meta: { filterVariant: "select" },
    filterFn: "equalsString",
  },
  {
    accessorKey: "import_at",
    header: "Import At",
    meta: { filterVariant: "dateRange" },
    cell: ({ row }) => <DateCell value={row.original.import_at} />,
  },
  {
    id: "note",
    accessorFn: (row) => row.note ?? "",
    header: "Note",
    cell: ({ row }) => (
      <span className="block max-w-xs truncate text-muted-foreground">
        {row.original.note ?? "—"}
      </span>
    ),
  },
  {
    id: "actions",
    enableSorting: false,
    enableColumnFilter: false,
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => <ChannelQueueActions queueEntry={row.original} />,
  },
]
