// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"

import type { ChannelOutput } from "@/client"
import type { ChannelRow } from "@/components/Channels/ChannelList/useScopedChannels"
import { CopyId } from "@/components/Common/CopyId"
import { cn } from "@/lib/utils"
import { visibilityDotClass, visibilityLabel } from "@/lib/visibility"
import { ChannelActionsMenu } from "./ChannelActionsMenu"

export type ChannelTableData = ChannelOutput & { pending?: boolean }

// Score is admin-only and only present on rows fetched from the admin endpoint.
export function channelScoreColumn<T extends object>(): ColumnDef<T> {
  const score = (row: T) => ("score" in row ? (row.score as number) : null)
  return {
    id: "score",
    accessorFn: score,
    header: "Score",
    meta: { filterVariant: "range" },
    cell: ({ row }) => (
      <span className="tabular-nums">{score(row.original) ?? "—"}</span>
    ),
  }
}

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

export function ownedChannelColumns(isAdmin: boolean): ColumnDef<ChannelRow>[] {
  const cols = [...columns] as ColumnDef<ChannelRow>[]
  if (isAdmin) {
    // Keep the actions column last.
    cols.splice(cols.length - 1, 0, channelScoreColumn<ChannelRow>())
  }
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
      <span className="text-muted-foreground tabular-nums">
        {row.original.channel_number ?? "—"}
      </span>
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
    cell: ({ row }) => (
      <div className="flex justify-end">
        {row.original.pending ? null : (
          <ChannelActionsMenu channel={row.original} />
        )}
      </div>
    ),
  },
]
