// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"

import type { ChannelPublicOutput } from "@/client"
import type { ChannelRow } from "@/components/Channels/ChannelList/useScopedChannels"
import { ChannelDescriptionCell, channelScoreColumn } from "./columns"

// Admins read this tab from the admin endpoint, which sorts and filters
// server-side; the public endpoint pages by score only, so those controls stay
// off unless an admin is viewing.
export function publicChannelColumns(
  isAdmin: boolean,
): ColumnDef<ChannelRow>[] {
  const cols = publicColumns.map((column) => ({
    ...column,
    enableSorting: isAdmin,
    enableColumnFilter: isAdmin,
  })) as ColumnDef<ChannelRow>[]
  if (isAdmin) {
    cols.push(channelScoreColumn<ChannelRow>())
  }
  return cols
}

const publicColumns: ColumnDef<ChannelPublicOutput>[] = [
  {
    accessorKey: "channel_number",
    header: "Ch#",
    enableSorting: false,
    enableColumnFilter: false,
    cell: ({ row }) => (
      <span className="text-muted-foreground tabular-nums">
        {row.original.channel_number ?? "—"}
      </span>
    ),
  },
  {
    accessorKey: "name",
    header: "Name",
    enableSorting: false,
    enableColumnFilter: false,
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
  },
  {
    accessorKey: "description",
    header: "Description",
    enableSorting: false,
    enableColumnFilter: false,
    cell: ({ row }) => (
      <ChannelDescriptionCell description={row.original.description} />
    ),
  },
  {
    accessorKey: "username",
    header: "Created By",
    enableSorting: false,
    enableColumnFilter: false,
    cell: ({ row }) => {
      if (!row.original.user_id) {
        return <span className="text-muted-foreground">—</span>
      }

      return (
        <Link
          to="/users/$userId/channels"
          params={{ userId: row.original.user_id }}
          className="underline hover:text-foreground"
        >
          {row.original.username || "Unnamed User"}
        </Link>
      )
    },
  },
]
