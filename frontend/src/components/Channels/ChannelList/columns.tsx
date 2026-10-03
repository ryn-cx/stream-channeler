// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"

import type { ChannelOutput } from "@/client"
import type { ChannelRow } from "@/components/Channels/ChannelList/useScopedChannels"
import { ChannelNumber } from "@/components/Channels/ChannelNumber"
import { CopyId } from "@/components/Common/CopyId"
import { isLoggedIn } from "@/hooks/useAuth"
import { cn } from "@/lib/utils"
import { visibilityDotClass, visibilityLabel } from "@/lib/visibility"
import { ChannelActionsMenu } from "./ChannelActionsMenu"
import { FavoriteChannel } from "./FavoriteChannel"

export type ChannelTableData = ChannelOutput & { pending?: boolean }

// TODO: Validate
export function channelFavoriteCountColumn<T extends object>(): ColumnDef<T> {
  // TODO: Validate
  const favoriteCount = (row: T) =>
    "favorite_count" in row ? (row.favorite_count as number) : null
  return {
    id: "favorite_count",
    accessorFn: favoriteCount,
    header: "Favorites",
    meta: { filterVariant: "range" },
    cell: ({ row }) => (
      <span className="tabular-nums">{favoriteCount(row.original) ?? "—"}</span>
    ),
  }
}

// TODO: Validate
export function ChannelDescriptionCell({
  description,
}: {
  description?: string | null
}) {
  if (!description) {
    return <span className="text-muted-foreground italic">None</span>
  }
  return (
    <div
      className="max-w-[320px] truncate text-muted-foreground"
      title={description}
    >
      {description}
    </div>
  )
}

// TODO: Validate
export function ownedChannelColumns(): ColumnDef<ChannelRow>[] {
  const cols = [...columns] as ColumnDef<ChannelRow>[]
  // Keep the actions column last.
  cols.splice(cols.length - 1, 0, channelFavoriteCountColumn<ChannelRow>())
  return cols
}

export const columns: ColumnDef<ChannelTableData>[] = [
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => <CopyId id={row.original.id} />,
  },
  {
    accessorKey: "channel_number",
    header: "Ch#",
    cell: ({ row }) => (
      <ChannelNumber channelNumber={row.original.channel_number} />
    ),
  },
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => {
      if (row.original.pending) {
        return (
          <span className="text-muted-foreground">{row.original.name}</span>
        )
      }

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
    meta: { filterVariant: "select" },
    filterFn: "equalsString",
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
    accessorKey: "description",
    header: "Description",
    cell: ({ row }) => (
      <ChannelDescriptionCell description={row.original.description} />
    ),
    meta: {
      filterVariant: "text",
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
    enableSorting: false,
    enableColumnFilter: false,
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) =>
      row.original.pending ? null : (
        <div className="flex justify-end gap-1">
          {isLoggedIn() && <FavoriteChannel channelId={row.original.id} />}
          <ChannelActionsMenu channel={row.original} />
        </div>
      ),
  },
]
