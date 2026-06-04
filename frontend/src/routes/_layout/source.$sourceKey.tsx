// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { ArrowLeft, Tv } from "lucide-react"

import { OpenAPI } from "@/client"
import { request } from "@/client/core/request"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import { DataTableSkeleton } from "@/components/Common/DataTableSkeleton"
import { EmptyState } from "@/components/Common/EmptyState"
import AddShow from "@/components/Plugin/AddShow"
import {
  type ShowTableData,
  showColumns,
} from "@/components/Plugin/showColumns"
import { Button } from "@/components/ui/button"
import { isLoggedIn } from "@/hooks/useAuth"
import { usePersistedJsonState } from "@/hooks/usePersistedState"

function getShowsQueryOptions(sourceKey: string) {
  return {
    queryFn: () =>
      request(OpenAPI, {
        method: "GET",
        url: "/api/v1/sources/{source_id}/shows",
        path: { source_id: sourceKey },
      }) as Promise<ShowTableData[]>,
    queryKey: ["sources", sourceKey, "shows"],
  }
}

export const Route = createFileRoute("/_layout/source/$sourceKey")({
  component: SourceDetailPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Source Shows - Stream Channeler" }],
  }),
})

function ShowsTableContent() {
  const { sourceKey } = Route.useParams()
  const { data: shows } = useQuery(getShowsQueryOptions(sourceKey))
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>("shows-column-visibility", {
      key: false,
      id: false,
    })

  const table = useReactTable({
    data: shows ?? [],
    columns: showColumns,
    state: {
      columnVisibility,
    },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-2 px-[4%] pt-4 pb-2">
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => window.history.back()}
          >
            <ArrowLeft />
          </Button>
          <h1 className="text-2xl font-bold tracking-tight">Shows</h1>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <AddShow sourceKey={sourceKey} />
          <ColumnVisibilityButton table={table} />
        </div>
      </div>
      {!shows ? (
        <div className="px-[4%]">
          <DataTableSkeleton table={table} />
        </div>
      ) : shows.length === 0 ? (
        <EmptyState
          icon={Tv}
          title="This source has no shows yet"
          description="Add a show to get started"
        />
      ) : (
        <div className="px-[4%]">
          <DataTable
            columns={showColumns}
            data={shows}
            columnVisibility={columnVisibility}
            onColumnVisibilityChange={setColumnVisibility}
          />
        </div>
      )}
    </>
  )
}

function SourceDetailPage() {
  return (
    <div className="flex flex-col gap-6">
      <ShowsTableContent />
    </div>
  )
}
