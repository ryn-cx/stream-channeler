// TODO: Validate
import type { ColumnDef, VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { ArrowLeft, type LucideIcon } from "lucide-react"
import type { ReactNode } from "react"

import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import { DataTableSkeleton } from "@/components/Common/DataTableSkeleton"
import { EmptyState } from "@/components/Common/EmptyState"
import { MediaSubNav } from "@/components/Media/MediaSubNav"
import { Button } from "@/components/ui/button"
import { usePersistedJsonState } from "@/hooks/usePersistedState"

interface DetailTablePageProps<TData extends { id: string }> {
  title: string
  columns: ColumnDef<TData>[]
  /** The fetched rows, or `undefined` while loading. */
  data: TData[] | undefined
  /** localStorage key for column visibility (shared with the list page). */
  columnVisibilityKey: string
  defaultHidden?: VisibilityState
  emptyIcon: LucideIcon
  emptyTitle: string
  emptyDescription: string
  /** Header controls beside the column-visibility toggle (e.g. an "add" button). */
  headerActions?: ReactNode
}

/**
 * Shared layout for a parent's nested-media table (a source's shows, a show's
 * seasons, etc.): the sub-nav, a back button + title, header actions, and the
 * skeleton / empty-state / table body. Pages own the data fetch and pass `data` in.
 */
export function DetailTablePage<TData extends { id: string }>({
  title,
  columns,
  data,
  columnVisibilityKey,
  defaultHidden = { key: false, id: false },
  emptyIcon,
  emptyTitle,
  emptyDescription,
  headerActions,
}: DetailTablePageProps<TData>) {
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>(columnVisibilityKey, defaultHidden)

  const table = useReactTable({
    data: data ?? [],
    columns,
    state: { columnVisibility },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <div className="flex flex-col gap-6">
      <MediaSubNav />
      <div className="flex flex-wrap items-center justify-between gap-2 px-[4%] pt-4 pb-2">
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => window.history.back()}
          >
            <ArrowLeft />
          </Button>
          <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {headerActions}
          <ColumnVisibilityButton table={table} />
        </div>
      </div>
      {!data ? (
        <div className="px-[4%]">
          <DataTableSkeleton table={table} />
        </div>
      ) : data.length === 0 ? (
        <EmptyState
          icon={emptyIcon}
          title={emptyTitle}
          description={emptyDescription}
        />
      ) : (
        <div className="px-[4%]">
          <DataTable
            columns={columns}
            data={data}
            columnVisibility={columnVisibility}
            onColumnVisibilityChange={setColumnVisibility}
          />
        </div>
      )}
    </div>
  )
}
