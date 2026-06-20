// TODO: Validate
import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { createFileRoute, Link, redirect } from "@tanstack/react-router"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { ArrowLeft, Database } from "lucide-react"
import { type ReactNode, useMemo, useState } from "react"

import { OpenAPI } from "@/client"
import { request } from "@/client/core/request"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import { DataTableSkeleton } from "@/components/Common/DataTableSkeleton"
import { EmptyState } from "@/components/Common/EmptyState"
import AddFile from "@/components/Plugin/AddFile"
import AddSource from "@/components/Plugin/AddSource"
import {
  createFileColumns,
  type FileTableData,
} from "@/components/Plugin/fileColumns"
import {
  type SourceTableData,
  sourceColumns,
} from "@/components/Plugin/sourceColumns"
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import { usePersistedJsonState } from "@/hooks/usePersistedState"

type PluginView = "sources" | "files"

function getSourcesQueryOptions(pluginId: string) {
  return {
    queryFn: () =>
      request(OpenAPI, {
        method: "GET",
        url: "/api/v1/plugins/{plugin_id}/sources",
        path: { plugin_id: pluginId },
      }) as Promise<SourceTableData[]>,
    queryKey: ["plugins", pluginId, "sources"],
  }
}

function getFilesQueryOptions(pluginId: string, contentFilter: string) {
  return {
    queryFn: () =>
      request(OpenAPI, {
        method: "GET",
        url: "/api/v1/plugins/{plugin_id}/files",
        path: { plugin_id: pluginId },
        query: contentFilter ? { content: contentFilter } : {},
      }) as Promise<FileTableData[]>,
    queryKey: ["plugins", pluginId, "files", { content: contentFilter }],
    placeholderData: keepPreviousData,
  }
}

export const Route = createFileRoute("/_layout/plugin/$pluginId")({
  component: PluginDetailPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Plugin Sources - Stream Channeler" }],
  }),
})

function PageHeader({
  title,
  toggle,
  actions,
}: {
  title: string
  toggle: ReactNode
  actions: ReactNode
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 px-[4%] pt-4 pb-2">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/plugins">
            <ArrowLeft />
          </Link>
        </Button>
        <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
        {toggle}
      </div>
      <div className="flex flex-wrap items-center gap-2">{actions}</div>
    </div>
  )
}

function SourcesTableContent({ toggle }: { toggle: ReactNode }) {
  const { pluginId } = Route.useParams()
  const { data: sources } = useQuery(getSourcesQueryOptions(pluginId))
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>("sources-column-visibility", {
      key: false,
      id: false,
    })
  const table = useReactTable({
    data: sources ?? [],
    columns: sourceColumns,
    state: {
      columnVisibility,
    },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <>
      <PageHeader
        title="Sources"
        toggle={toggle}
        actions={
          <>
            <AddSource pluginId={pluginId} />
            <ColumnVisibilityButton table={table} />
          </>
        }
      />
      {!sources ? (
        <div className="px-[4%]">
          <DataTableSkeleton table={table} />
        </div>
      ) : sources.length === 0 ? (
        <EmptyState
          icon={Database}
          title="This plugin has no sources yet"
          description="Add a source to get started"
        />
      ) : (
        <div className="px-[4%]">
          <DataTable
            columns={sourceColumns}
            data={sources}
            columnVisibility={columnVisibility}
            onColumnVisibilityChange={setColumnVisibility}
          />
        </div>
      )}
    </>
  )
}

function FilesTableContent({ toggle }: { toggle: ReactNode }) {
  const { pluginId } = Route.useParams()
  // The content search is server-side; the input is debounced in the table
  // header so the query only fires once the user stops typing.
  const [contentFilter, setContentFilter] = useState("")

  const { data: files } = useQuery(
    getFilesQueryOptions(pluginId, contentFilter),
  )
  const columns = useMemo(
    () =>
      createFileColumns({
        value: contentFilter,
        onChange: setContentFilter,
      }),
    [contentFilter],
  )
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>("files-column-visibility", {
      id: false,
    })
  const table = useReactTable({
    data: files ?? [],
    columns,
    state: {
      columnVisibility,
    },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <>
      <PageHeader
        title="Files"
        toggle={toggle}
        actions={
          <>
            <AddFile pluginId={pluginId} />
            <ColumnVisibilityButton table={table} />
          </>
        }
      />
      {!files ? (
        <div className="px-[4%]">
          <DataTableSkeleton table={table} />
        </div>
      ) : files.length === 0 && !contentFilter ? (
        <EmptyState
          icon={Database}
          title="This plugin has no files yet"
          description="Add a file to get started"
        />
      ) : (
        <div className="px-[4%]">
          <DataTable
            columns={columns}
            data={files}
            columnVisibility={columnVisibility}
            onColumnVisibilityChange={setColumnVisibility}
          />
        </div>
      )}
    </>
  )
}

function PluginDetailPage() {
  const { user } = useAuth()
  const isAdmin = user?.is_superuser ?? false
  const [view, setView] = usePersistedJsonState<PluginView>(
    "plugin-detail-view",
    "sources",
  )

  const toggle = isAdmin ? (
    <Tabs value={view} onValueChange={(value) => setView(value as PluginView)}>
      <TabsList>
        <TabsTrigger value="sources">Sources</TabsTrigger>
        <TabsTrigger value="files">Files</TabsTrigger>
      </TabsList>
    </Tabs>
  ) : null

  return (
    <div className="flex flex-col gap-6">
      {isAdmin && view === "files" ? (
        <FilesTableContent toggle={toggle} />
      ) : (
        <SourcesTableContent toggle={toggle} />
      )}
    </div>
  )
}
