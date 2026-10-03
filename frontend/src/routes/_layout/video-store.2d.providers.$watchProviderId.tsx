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

type TwoDimensionalProviderStoreSearch = TitleCardFilters & {
  page?: number
  region?: string
}

export const Route = createFileRoute(
  "/_layout/video-store/2d/providers/$watchProviderId",
)({
  component: TwoDimensionalProviderStore,
  validateSearch: (
    search: Record<string, unknown>,
  ): TwoDimensionalProviderStoreSearch => ({
    page:
      typeof search.page === "number" && search.page > 1
        ? search.page
        : undefined,
    ...readTitleCardFilters(search),
    region:
      typeof search.region === "string" && search.region.length === 2
        ? search.region.toUpperCase()
        : undefined,
  }),
  head: () => ({
    meta: [{ title: "2D Store - Stream Channeler" }],
  }),
})

// TODO: Validate
function TwoDimensionalProviderStore() {
  const { watchProviderId } = Route.useParams()
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  const region = search.region
  const activeRegion = region ?? "US"
  const pageIndex = (search.page ?? 1) - 1
  const filters = pickTitleCardFilters(search)
  const openMedia = useOpenMedia()

  const { data: providers } = useQuery({
    queryKey: ["video-store-watch-providers", activeRegion],
    queryFn: () =>
      VideoStoreService.getStoreWatchProviders({ region: activeRegion }),
    refetchOnWindowFocus: false,
  })
  const provider = providers?.find((entry) => entry.id === watchProviderId)

  const { data: facets } = useQuery({
    queryKey: [
      "video-store-provider-title-card-facets",
      watchProviderId,
      activeRegion,
    ],
    queryFn: () =>
      VideoStoreService.getProviderTitleCardFacets({
        watchProviderId,
        region: activeRegion,
      }),
    refetchOnWindowFocus: false,
  })

  const { data, isLoading, isPlaceholderData } = useQuery({
    queryKey: [
      "video-store-provider-title-cards",
      watchProviderId,
      activeRegion,
      pageIndex,
      filters,
    ],
    queryFn: () =>
      VideoStoreService.getProviderTitleCards({
        watchProviderId,
        region: activeRegion,
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
    navigate({ search: { ...filters, region, page: nextPageIndex + 1 } })
    window.scrollTo(0, 0)
  }

  return (
    <div className="flex flex-col gap-4 px-[4%] py-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Link
          to="/video-store"
          search={{ region: activeRegion }}
          className="flex w-fit items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          Back to the video store
        </Link>
        <a
          href="https://www.justwatch.com"
          target="_blank"
          rel="noreferrer"
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          Streaming data by JustWatch
        </a>
      </div>

      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          {provider?.name ?? "2D Store"}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {data?.total !== undefined
            ? `${activeRegion} · ${data.total.toLocaleString()} titles`
            : "Loading titles"}
        </p>
      </div>

      <TitleCardFilterBar
        filters={filters}
        facets={facets}
        onChange={(next) => navigate({ search: { ...next, region } })}
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
            onSelect={(selected: TitleGroup) =>
              openMedia({ kind: "title", titleId: selected.tmdbTitleId })
            }
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
