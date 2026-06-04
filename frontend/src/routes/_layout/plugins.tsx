// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { Puzzle } from "lucide-react"

import { OpenAPI } from "@/client"
import { request } from "@/client/core/request"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import { DataTableSkeleton } from "@/components/Common/DataTableSkeleton"
import { EmptyState } from "@/components/Common/EmptyState"
import { PageHeader } from "@/components/Common/PageHeader"
import AddPlugin from "@/components/Plugin/AddPlugin"
import { columns, type PluginTableData } from "@/components/Plugin/columns"
import { isLoggedIn } from "@/hooks/useAuth"
import { usePersistedJsonState } from "@/hooks/usePersistedState"

function getPluginsQueryOptions() {
  return {
    queryFn: () =>
      request(OpenAPI, {
        method: "GET",
        url: "/api/v1/plugins",
      }) as Promise<PluginTableData[]>,
    queryKey: ["plugins"],
    refetchOnWindowFocus: false,
    placeholderData: (previousData: any) => previousData,
  }
}

export const Route = createFileRoute("/_layout/plugins")({
  component: PluginPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Plugins - Stream Channeler" }],
  }),
})

function PluginsTableContent() {
  const { data: plugins, isPlaceholderData } = useQuery(
    getPluginsQueryOptions(),
  )
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>("plugins-column-visibility", {
      key: false,
      id: false,
    })

  const table = useReactTable({
    data: plugins ?? [],
    columns,
    state: {
      columnVisibility,
    },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <div
      className={
        isPlaceholderData
          ? "opacity-60 transition-opacity duration-200"
          : undefined
      }
    >
      <PageHeader title="Plugins">
        <AddPlugin />
        <ColumnVisibilityButton table={table} />
      </PageHeader>
      {!plugins ? (
        <div className="px-[4%]">
          <DataTableSkeleton table={table} />
        </div>
      ) : plugins.length === 0 ? (
        <EmptyState
          icon={Puzzle}
          title="You don't have any plugins yet"
          description="Add a plugin to get started"
        />
      ) : (
        <div className="px-[4%]">
          <DataTable
            columns={columns}
            data={plugins}
            columnVisibility={columnVisibility}
            onColumnVisibilityChange={setColumnVisibility}
          />
        </div>
      )}
    </div>
  )
}

function PluginPage() {
  return (
    <div className="flex flex-col gap-6">
      <PluginsTableContent />
    </div>
  )
}
