// TODO: Validate
import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"
import { VideoStoreService } from "@/client"
import {
  pickTitleCardFilters,
  readTitleCardFilters,
  TitleCardFilterBar,
  type TitleCardFilters,
} from "@/components/Channels/TitleCardFilters"
import { TitleCards, type TitleGroup } from "@/components/Channels/TitleCards"
import { TrailerButton } from "@/components/Channels/TrailerButton"
import { PageControls } from "@/components/Common/PageControls"
import { Skeleton } from "@/components/ui/skeleton"
import { useOpenMedia } from "@/hooks/useOpenMedia"

type TwoDimensionalStoreSearch = TitleCardFilters & { page?: number }

export const Route = createFileRoute("/_layout/video-store/2d/$sourceId")({
  component: TwoDimensionalStore,
  validateSearch: (
    search: Record<string, unknown>,
  ): TwoDimensionalStoreSearch => ({
    page:
      typeof search.page === "number" && search.page > 1
        ? search.page
        : undefined,
    ...readTitleCardFilters(search),
  }),
  head: () => ({
    meta: [{ title: "2D Store - Stream Channeler" }],
  }),
})

// TODO: Validate
function TwoDimensionalStore() {
  const { sourceId } = Route.useParams()
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  const pageIndex = (search.page ?? 1) - 1
  const filters = pickTitleCardFilters(search)
  const openMedia = useOpenMedia()

  const { data: sources } = useQuery({
    queryKey: ["video-store-sources"],
    queryFn: () => VideoStoreService.getStoreSources(),
    refetchOnWindowFocus: false,
  })
  const source = sources?.find((entry) => entry.id === sourceId)

  const { data: facets } = useQuery({
    queryKey: ["video-store-title-card-facets", sourceId],
    queryFn: () => VideoStoreService.getSourceTitleCardFacets({ sourceId }),
    refetchOnWindowFocus: false,
  })

  const { data, isLoading, isPlaceholderData } = useQuery({
    queryKey: ["video-store-title-cards", sourceId, pageIndex, filters],
    queryFn: () =>
      VideoStoreService.getSourceTitleCards({
        sourceId,
        offset: pageIndex * 100,
        limit: 100,
        ...filters,
      }),
    placeholderData: keepPreviousData,
    refetchOnWindowFocus: false,
  })

  const pageCount = Math.max(1, Math.ceil((data?.total ?? 0) / 100))
  const tmdbTitles = data?.tmdb_titles ?? {}
  const titles = (data?.titles ?? []).filter((title) =>
    title.tmdb_title_id
      ? !!tmdbTitles[title.tmdb_title_id]?.name
      : !!title.name,
  )

  // TODO: Validate
  const goToPage = (nextPageIndex: number) => {
    navigate({ search: { ...filters, page: nextPageIndex + 1 } })
    window.scrollTo(0, 0)
  }

  return (
    <div className="flex flex-col gap-4 px-[4%] py-6">
      <Link
        to="/video-store"
        className="flex w-fit items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" />
        Back to the video store
      </Link>

      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          {source?.key ?? "2D Store"}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {data?.total !== undefined
            ? `${data.total.toLocaleString()} titles`
            : "Loading titles"}
        </p>
      </div>

      <TitleCardFilterBar
        filters={filters}
        facets={facets}
        onChange={(next) => navigate({ search: next })}
      />

      {isLoading ? (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(min(100%,320px),320px))] gap-3">
          {Array.from({ length: 12 }).map((_, index) => (
            <Skeleton key={index} className="h-64 w-full rounded-lg" />
          ))}
        </div>
      ) : titles.length === 0 ? (
        <p className="text-sm text-muted-foreground">No titles found.</p>
      ) : (
        <div
          className={`transition-opacity duration-200 ${isPlaceholderData ? "opacity-60" : ""}`}
        >
          <TitleCards
            titles={titles}
            sources={data?.sources ?? {}}
            tmdbTitles={tmdbTitles}
            tmdbSources={data?.tmdb_sources ?? {}}
            stats={data?.stats ?? {}}
            details={data?.details ?? {}}
            renderActions={(group: TitleGroup) => (
              <TrailerButton titleId={group.tmdbTitleId} name={group.name} />
            )}
            onSelect={(selected: TitleGroup) => {
              const grouped = (data?.titles ?? []).filter(
                (title) =>
                  (title.tmdb_title_id ?? title.id) === selected.tmdbTitleId,
              )
              const opened = grouped.find(
                (title) => title.source_id === sourceId,
              )
              if (!opened) {
                openMedia({ kind: "title", titleId: selected.tmdbTitleId })
                return
              }
              openMedia({
                kind: "title",
                titleId: opened.id,
                extraLinks: grouped.flatMap((title) => {
                  const titleSource = data?.sources?.[title.source_id]
                  return title.id !== opened.id && title.url && titleSource
                    ? [
                        {
                          label: titleSource.key,
                          href: title.url,
                          faviconUrl: titleSource.favicon_url,
                        },
                      ]
                    : []
                }),
              })
            }}
          />
        </div>
      )}

      <PageControls
        pageIndex={pageIndex}
        pageCount={pageCount}
        onPageChange={goToPage}
      />
    </div>
  )
}
