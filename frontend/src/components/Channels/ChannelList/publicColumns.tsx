// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"

import type { ChannelListOutput } from "@/client"
import type { ChannelRow } from "@/components/Channels/ChannelList/useScopedChannels"
import { ChannelDescriptionCell, channelScoreColumn } from "./columns"

// `score` is only populated for a `Channel`'s owner or an admin, so the column is
// pushed for admins alone. Sorting and filtering stay off for everyone else purely
// to keep this tab's presentation unchanged — the endpoint now serves them to any
// viewer, so this gate can be lifted whenever that is wanted.
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

const publicColumns: ColumnDef<ChannelListOutput>[] = [
  {
    accessorKey: "channel_number",
    header: "Ch#",
    enableSorting: false,
    enableColumnFilter: false,
    cell: ({ row }) => (
      <span className="text-muted-foreground tabular-nums">
        {row.original.custom_channel_number ??
          row.original.channel_number ??
          "—"}
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
          {row.original.custom_name ?? row.original.name}
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
      // The API reveals an anonymous channel's real creator to admins and the
      // owner, but this public listing must still present it anonymously.
      if (!row.original.user_id || row.original.anonymous) {
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
