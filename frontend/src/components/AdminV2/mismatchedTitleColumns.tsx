// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"

import type { MismatchedTitleOutput } from "@/client"
import { ExternalLinkButton } from "@/components/Admin/tmdbMatchColumns"
import { DateCell } from "@/components/Common/TableCells"
import { EditTitleById } from "@/components/Titles/EditTitleById"
import { cn } from "@/lib/utils"
import { MismatchedTitleActions } from "./MismatchedTitleActions"

// TODO: Validate
function TitleSummary({
  source,
  titleId,
  name,
  year,
  url,
  nameMismatched,
  yearMismatched,
  editLabel,
  openLabel,
}: {
  source: string
  titleId: string
  name: string | null | undefined
  year: number | null | undefined
  url: string | null | undefined
  nameMismatched: boolean
  yearMismatched: boolean
  editLabel?: string
  openLabel: string
}) {
  return (
    <div className="max-w-72 whitespace-normal wrap-break-word">
      <span className="block text-xs text-muted-foreground">{source}</span>
      <span className="flex flex-wrap items-center gap-1 font-medium">
        <Link
          to="/seasons"
          search={{ title_id: titleId }}
          className="min-w-0 hover:underline"
        >
          <span className={cn(nameMismatched && "text-destructive")}>
            {name ?? "Unnamed"}
          </span>{" "}
          <span
            className={cn("tabular-nums", yearMismatched && "text-destructive")}
          >
            ({year ?? "Unknown"})
          </span>
        </Link>
        <EditTitleById titleId={titleId} label={editLabel} />
        <ExternalLinkButton url={url} label={openLabel} />
      </span>
    </div>
  )
}

// TODO: Validate
export const mismatchedTitleColumns: ColumnDef<MismatchedTitleOutput>[] = [
  {
    id: "title_name",
    accessorFn: (row) => row.title_name ?? "",
    header: "Title",
    meta: {
      cellClassName: "align-top",
      headerFilters: [
        { columnId: "source_key", label: "Source" },
        { columnId: "title_name", label: "Title" },
        { columnId: "title_year", label: "Year" },
      ],
    },
    cell: ({ row }) => (
      <TitleSummary
        source={`${row.original.source_key} · ${row.original.plugin_name}`}
        titleId={row.original.title_id}
        name={row.original.title_name}
        year={row.original.title_year}
        url={row.original.title_url}
        nameMismatched={row.original.name_mismatched}
        yearMismatched={row.original.year_mismatched}
        openLabel="Open this title on the site it came from"
      />
    ),
  },
  {
    id: "tmdb_title_name",
    accessorFn: (row) => row.tmdb_title_name ?? "",
    header: "Linked To",
    meta: {
      cellClassName: "align-top",
      headerFilters: [
        { columnId: "tmdb_title_name", label: "Title" },
        { columnId: "tmdb_title_year", label: "Year" },
      ],
    },
    cell: ({ row }) => (
      <TitleSummary
        source="TMDB"
        titleId={row.original.tmdb_title_id}
        name={row.original.tmdb_title_name}
        year={row.original.tmdb_title_year}
        url={row.original.tmdb_url}
        nameMismatched={row.original.name_mismatched}
        yearMismatched={row.original.year_mismatched}
        editLabel="Edit this TMDB title"
        openLabel="Open this title on TMDB"
      />
    ),
  },
  {
    id: "title_year",
    accessorFn: (row) => row.title_year ?? 0,
    header: "Year",
    cell: ({ row }) => (
      <span className="tabular-nums">{row.original.title_year ?? "-"}</span>
    ),
  },
  {
    id: "tmdb_title_year",
    accessorFn: (row) => row.tmdb_title_year ?? 0,
    header: "TMDB Year",
    cell: ({ row }) => (
      <span className="tabular-nums">
        {row.original.tmdb_title_year ?? "-"}
      </span>
    ),
  },
  {
    id: "plugin_name",
    accessorFn: (row) => row.plugin_name,
    header: "Plugin",
    meta: { filterVariant: "select" },
    filterFn: "equalsString",
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm">
        {row.original.plugin_name}
      </span>
    ),
  },
  {
    id: "source_key",
    accessorFn: (row) => row.source_key,
    header: "Source",
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm">
        {row.original.source_key}
      </span>
    ),
  },
  {
    id: "media_type",
    accessorFn: (row) => row.media_type ?? "",
    header: "Media Type",
    meta: { filterVariant: "select", cellClassName: "align-top" },
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
    id: "linked_at",
    accessorFn: (row) => row.linked_at,
    header: "Linked",
    meta: { filterVariant: "dateRange", cellClassName: "align-top" },
    cell: ({ row }) => <DateCell value={row.original.linked_at} />,
  },
  {
    id: "actions",
    header: "Actions",
    meta: { cellClassName: "align-top" },
    enableSorting: false,
    enableColumnFilter: false,
    cell: ({ row }) => <MismatchedTitleActions entry={row.original} />,
  },
]
