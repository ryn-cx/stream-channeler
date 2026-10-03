// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"

import type { UnlinkedTitleOutput } from "@/client"
import { ExternalLinkButton } from "@/components/Admin/tmdbMatchColumns"
import { DateCell } from "@/components/Common/TableCells"
import { EditTitleById } from "@/components/Titles/EditTitleById"
import { MarkTitleAbsentButton } from "@/components/Titles/MarkTitleAbsentButton"

// TODO: Validate
export const unlinkedTitleColumns: ColumnDef<UnlinkedTitleOutput>[] = [
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
      <div className="max-w-72 whitespace-normal wrap-break-word">
        <span className="block text-xs text-muted-foreground">
          {row.original.source_key} · {row.original.plugin_name}
        </span>
        <span className="flex flex-wrap items-center gap-1 font-medium">
          <Link
            to="/seasons"
            search={{ title_id: row.original.id }}
            className="min-w-0 hover:underline"
          >
            {row.original.title_name ?? "Unnamed"}{" "}
            <span className="tabular-nums">
              ({row.original.title_year ?? "Unknown"})
            </span>
          </Link>
          <EditTitleById titleId={row.original.id} />
          <ExternalLinkButton
            url={row.original.title_url}
            label="Open this title on the site it came from"
          />
        </span>
      </div>
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
    id: "link_status",
    accessorFn: (row) => row.link_status ?? "",
    header: "Link Status",
    meta: { filterVariant: "select", cellClassName: "align-top" },
    filterFn: "equalsString",
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm">
        {row.original.link_status ?? "-"}
      </span>
    ),
  },
  {
    id: "created_at",
    accessorFn: (row) => row.created_at,
    header: "Added",
    meta: { filterVariant: "dateRange", cellClassName: "align-top" },
    cell: ({ row }) => <DateCell value={row.original.created_at} />,
  },
  {
    id: "actions",
    header: "Actions",
    meta: { cellClassName: "align-top" },
    enableSorting: false,
    enableColumnFilter: false,
    cell: ({ row }) => (
      <MarkTitleAbsentButton
        titleId={row.original.id}
        titleName={row.original.title_name}
      />
    ),
  },
]
