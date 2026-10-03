// TODO: Validate
import type { ColumnDef } from "@tanstack/react-table"

import type { TitleLinkHistoryOutput } from "@/client"
import { DateCell } from "@/components/Common/TableCells"
import { EditTitleById } from "@/components/Titles/EditTitleById"
import { Badge } from "@/components/ui/badge"
import { TitleLinkHistoryUndoButton } from "./TitleLinkHistoryUndoButton"

const KIND_LABELS: Record<string, string> = {
  link: "Linked",
  ignored: "Ignored",
  absent: "Not on TMDB",
}

// TODO: Validate
export const titleLinkHistoryColumns: ColumnDef<TitleLinkHistoryOutput>[] = [
  {
    id: "created_at",
    accessorFn: (row) => row.created_at,
    header: "When",
    meta: { filterVariant: "dateRange", cellClassName: "align-top" },
    cell: ({ row }) => <DateCell value={row.original.created_at} />,
  },
  {
    id: "kind",
    accessorFn: (row) => row.kind,
    header: "Action",
    meta: {
      filterVariant: "select",
      cellClassName: "align-top",
      filterOptions: [
        { label: "Linked", value: "link" },
        { label: "Ignored", value: "ignored" },
        { label: "Not on TMDB", value: "absent" },
      ],
    },
    filterFn: "equalsString",
    cell: ({ row }) => (
      <Badge variant={row.original.kind === "link" ? "secondary" : "outline"}>
        {KIND_LABELS[row.original.kind] ?? row.original.kind}
      </Badge>
    ),
  },
  {
    id: "title_name",
    accessorFn: (row) => row.title_name ?? "",
    header: "Title",
    meta: { cellClassName: "align-top" },
    cell: ({ row }) => (
      <span className="flex items-center gap-2">
        {row.original.title_url ? (
          <a
            href={row.original.title_url}
            target="_blank"
            rel="noreferrer"
            className="font-medium whitespace-normal wrap-break-word hover:underline"
          >
            {row.original.title_name ?? "Unnamed"}
          </a>
        ) : (
          <span className="font-medium whitespace-normal wrap-break-word">
            {row.original.title_name ?? "Unnamed"}
          </span>
        )}
        <EditTitleById titleId={row.original.title_id} />
      </span>
    ),
  },
  {
    id: "tmdb_title_name",
    accessorFn: (row) => row.tmdb_title_name ?? "",
    header: "Linked To",
    meta: { cellClassName: "align-top" },
    cell: ({ row }) => {
      const entry = row.original
      if (!entry.tmdb_title_id) {
        return <span className="text-muted-foreground">-</span>
      }
      return (
        <span className="flex items-center gap-2">
          {entry.tmdb_url ? (
            <a
              href={entry.tmdb_url}
              target="_blank"
              rel="noreferrer"
              className="whitespace-normal wrap-break-word hover:underline"
            >
              {entry.tmdb_title_name ?? "Unnamed"}
            </a>
          ) : (
            <span className="whitespace-normal wrap-break-word">
              {entry.tmdb_title_name ?? "Unnamed"}
            </span>
          )}
          <EditTitleById
            titleId={entry.tmdb_title_id}
            label="Edit this TMDB title"
          />
        </span>
      )
    },
  },
  {
    id: "source_key",
    accessorFn: (row) => row.source_key ?? "",
    header: "Source",
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm">
        {row.original.source_key ?? "-"}
      </span>
    ),
  },
  {
    id: "plugin_name",
    accessorFn: (row) => row.plugin_name ?? "",
    header: "Plugin",
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm">
        {row.original.plugin_name ?? "No plugin"}
      </span>
    ),
  },
  {
    id: "title_year",
    accessorFn: (row) => row.title_year ?? 0,
    header: "Year",
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.title_year ?? "-"}
      </span>
    ),
  },
  {
    id: "media_type",
    accessorFn: (row) => row.media_type ?? "",
    header: "Media Type",
    meta: { filterVariant: "select" },
    filterFn: "equalsString",
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.media_type ?? "-"}
      </span>
    ),
  },
  {
    id: "note",
    accessorFn: (row) => row.note ?? "",
    header: "Note",
    meta: { cellClassName: "align-top" },
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm">
        {row.original.note ?? "-"}
      </span>
    ),
  },
  {
    id: "actions",
    header: "Actions",
    meta: { cellClassName: "align-top" },
    enableSorting: false,
    enableColumnFilter: false,
    cell: ({ row }) => <TitleLinkHistoryUndoButton entry={row.original} />,
  },
]
