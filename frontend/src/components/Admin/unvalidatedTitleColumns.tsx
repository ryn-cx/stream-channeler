// TODO: Validate
import type { ColumnDef } from "@tanstack/react-table"

import type { UnvalidatedTitleOutput } from "@/client"
import { ExternalAnchor } from "@/components/ChannelCommon/InformationTable"
import { DateCell, TruncatedCell } from "@/components/Common/TableCells"
import EditTitle from "@/components/Titles/Edit"
import { ValidateTitleButton } from "./ValidateTitleButton"

// TODO: Validate
export const unvalidatedTitleColumns: ColumnDef<UnvalidatedTitleOutput>[] = [
  {
    id: "name",
    accessorFn: (row) => row.name ?? "",
    header: "Title",
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
    id: "source_key",
    accessorFn: (row) => row.source_key,
    header: "Source",
    meta: { filterVariant: "select" },
    filterFn: "equalsString",
  },
  {
    id: "linked_titles",
    // A row that mixes titles stands for each of them equally, so every one it
    // is linked to is listed rather than whichever came first.
    accessorFn: (row) =>
      row.linked_titles.length === 0
        ? "Its own record"
        : row.linked_titles.map((linked) => linked.name ?? "").join(", "),
    header: "Linked To",
    cell: ({ row }) =>
      row.original.linked_titles.length === 0 ? (
        <span className="text-muted-foreground text-sm">Its own record</span>
      ) : (
        <div className="flex flex-col gap-1">
          {row.original.linked_titles.map((linked) => (
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
              {linked.note ? (
                <span className="text-muted-foreground"> — {linked.note}</span>
              ) : null}
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
        <ValidateTitleButton
          titleId={row.original.id}
          titleName={row.original.name}
        />
        <EditTitle title={row.original} />
      </div>
    ),
  },
]
