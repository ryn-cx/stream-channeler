// TODO: Validate
import type { ColumnDef } from "@tanstack/react-table"

import type { UnvalidatedShowOutput } from "@/client"
import { ExternalAnchor } from "@/components/ChannelCommon/InformationTable"
import { DateCell, TruncatedCell } from "@/components/Common/TableCells"
import EditShow from "@/components/Shows/Edit"
import { ValidateShowButton } from "./ValidateShowButton"

// TODO: Validate
export const unvalidatedShowColumns: ColumnDef<UnvalidatedShowOutput>[] = [
  {
    id: "name",
    accessorFn: (row) => row.name ?? "",
    header: "Show",
    cell: ({ row }) =>
      row.original.url ? (
        <ExternalAnchor
          href={row.original.url}
          label={row.original.name ?? row.original.key}
        />
      ) : (
        <TruncatedCell value={row.original.name} />
      ),
  },
  {
    id: "year",
    accessorFn: (row) => row.year ?? "",
    header: "Year",
    cell: ({ row }) => (
      <span className="tabular-nums">{row.original.year ?? ""}</span>
    ),
  },
  {
    id: "plugin_name",
    accessorFn: (row) => row.plugin_name ?? "",
    header: "Plugin",
    meta: { filterVariant: "select" },
    filterFn: "equalsString",
  },
  {
    id: "source_name",
    accessorFn: (row) => row.source_name ?? "",
    header: "Source",
    meta: { filterVariant: "select" },
    filterFn: "equalsString",
  },
  {
    id: "linked_shows",
    // A row that mixes titles stands for each of them equally, so every one it
    // is linked to is listed rather than whichever came first.
    accessorFn: (row) =>
      row.linked_shows.length === 0
        ? "Its own record"
        : row.linked_shows.map((linked) => linked.name ?? "").join(", "),
    header: "Linked To",
    cell: ({ row }) =>
      row.original.linked_shows.length === 0 ? (
        <span className="text-muted-foreground text-sm">Its own record</span>
      ) : (
        <div className="flex flex-col gap-1">
          {row.original.linked_shows.map((linked) => (
            <span key={linked.id} className="text-sm">
              {linked.url ? (
                <ExternalAnchor
                  href={linked.url}
                  label={`${linked.name ?? "Unnamed"}${
                    linked.year ? ` (${linked.year})` : ""
                  }`}
                />
              ) : (
                (linked.name ?? "Unnamed")
              )}
            </span>
          ))}
        </div>
      ),
  },
  {
    id: "episode_count",
    accessorFn: (row) => row.episode_count,
    header: "Episodes",
    cell: ({ row }) => (
      <span className="tabular-nums">{row.original.episode_count}</span>
    ),
  },
  {
    id: "created_at",
    accessorFn: (row) => row.created_at,
    header: "Found",
    cell: ({ row }) => <DateCell value={row.original.created_at} />,
  },
  {
    id: "actions",
    header: "Actions",
    enableSorting: false,
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <ValidateShowButton
          showId={row.original.id}
          showName={row.original.name}
        />
        <EditShow show={row.original} />
      </div>
    ),
  },
]
