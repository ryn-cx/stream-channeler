// TODO: Validate
import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { Library } from "lucide-react"
import { useEffect, useState } from "react"
import { PluginsService, TitlesService } from "@/client"
import { PluginPicker } from "@/components/AllTitles/PluginPicker"
import { TitleGrid } from "@/components/AllTitles/TitleGrid"
import {
  BrowsePagination,
  useBrowsePagination,
} from "@/components/Common/BrowsePagination"
import { EmptyState } from "@/components/Common/EmptyState"
import { PageHeader } from "@/components/Common/PageHeader"
import { Input } from "@/components/ui/input"

type AllTitlesSearch = {
  plugin?: string
}

export const Route = createFileRoute("/_layout/all-titles")({
  component: AllTitles,
  validateSearch: (search: Record<string, unknown>): AllTitlesSearch => ({
    plugin: typeof search.plugin === "string" ? search.plugin : undefined,
  }),
  head: () => ({
    meta: [
      {
        title: "All Titles On... - Stream Channeler",
      },
    ],
  }),
})

// TODO: Validate
function AllTitles() {
  const { plugin } = Route.useSearch()
  const navigate = useNavigate()
  const [searchInput, setSearchInput] = useState("")
  const [search, setSearch] = useState("")
  const [pagination, setPagination] = useBrowsePagination(
    "all-titles-browse-page-size",
  )

  useEffect(() => {
    const timeout = setTimeout(() => setSearch(searchInput), 300)
    return () => clearTimeout(timeout)
  }, [searchInput])

  const { data: plugins } = useQuery({
    queryKey: ["browsable-plugins"],
    queryFn: () => PluginsService.browsablePlugins(),
  })

  const { data, isPlaceholderData } = useQuery({
    queryKey: [
      "all-titles",
      plugin,
      search,
      pagination.pageIndex,
      pagination.pageSize,
    ],
    queryFn: () =>
      TitlesService.browseTitles({
        pluginKey: plugin ?? "",
        search: search || undefined,
        offset: pagination.pageIndex * pagination.pageSize,
        limit: pagination.pageSize,
      }),
    enabled: Boolean(plugin),
    placeholderData: keepPreviousData,
  })

  // TODO: Validate
  const selectPlugin = (pluginKey: string) => {
    setPagination((current) => ({ ...current, pageIndex: 0 }))
    navigate({ to: "/all-titles", search: { plugin: pluginKey } })
  }

  // TODO: Validate
  const changeSearch = (value: string) => {
    setPagination((current) => ({ ...current, pageIndex: 0 }))
    setSearchInput(value)
  }

  const titles = data?.data ?? []

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="All Titles On..."
        description="Everything one website says it carries, as that website has it."
      >
        <PluginPicker
          plugins={plugins ?? []}
          value={plugin ?? null}
          onValueChange={selectPlugin}
        />
        <Input
          value={searchInput}
          onChange={(event) => changeSearch(event.target.value)}
          placeholder="Search titles"
          className="w-[220px]"
          disabled={!plugin}
        />
      </PageHeader>

      {!plugin ? (
        <EmptyState
          icon={Library}
          title="Choose a website"
          description="Pick a website to see every title it carries."
        />
      ) : titles.length === 0 ? (
        <EmptyState
          icon={Library}
          title="No titles to show"
          description={
            search
              ? `Nothing on ${plugin} matches "${search}".`
              : `Nothing has been imported from ${plugin} yet.`
          }
        />
      ) : (
        <div
          className={
            isPlaceholderData
              ? "flex flex-col gap-4 opacity-60 transition-opacity duration-200"
              : "flex flex-col gap-4"
          }
        >
          <TitleGrid titles={titles} />
          <BrowsePagination
            pagination={pagination}
            onPaginationChange={setPagination}
            rowCount={data?.total_count ?? 0}
            itemLabel="Titles"
          />
        </div>
      )}
    </div>
  )
}
