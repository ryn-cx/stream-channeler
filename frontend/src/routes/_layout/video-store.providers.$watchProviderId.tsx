// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"
import { useCallback } from "react"
import { VideoStoreService } from "@/client"
import {
  fetchProviderTitlePage,
  PROVIDER_TITLE_PAGE,
} from "@/components/Channels/Channel3D/providerTitles"
import { StoreScreen } from "@/components/Channels/Channel3D/StoreScreen"

type ProviderStoreSearch = { region?: string }

export const Route = createFileRoute(
  "/_layout/video-store/providers/$watchProviderId",
)({
  component: ProviderStore,
  validateSearch: (search: Record<string, unknown>): ProviderStoreSearch => ({
    region:
      typeof search.region === "string" && search.region.length === 2
        ? search.region.toUpperCase()
        : undefined,
  }),
  head: () => ({
    meta: [{ title: "Video Store - Stream Channeler" }],
  }),
})

// TODO: Validate
function ProviderStore() {
  const { watchProviderId } = Route.useParams()
  const { region } = Route.useSearch()
  const activeRegion = region ?? "US"

  const { data: providers } = useQuery({
    queryKey: ["video-store-watch-providers", activeRegion],
    queryFn: () =>
      VideoStoreService.getStoreWatchProviders({ region: activeRegion }),
    refetchOnWindowFocus: false,
  })
  const provider = providers?.find((entry) => entry.id === watchProviderId)

  const fetchPage = useCallback(
    (offset: number) =>
      fetchProviderTitlePage(watchProviderId, activeRegion, offset),
    [watchProviderId, activeRegion],
  )

  return (
    <StoreScreen
      storeKey={`${watchProviderId}-${activeRegion}`}
      storeName={provider?.name || "Video Store"}
      pageSize={PROVIDER_TITLE_PAGE}
      fetchPage={fetchPage}
      emptyMessage={`Nothing is streaming here in ${activeRegion} right now.`}
      back={
        <>
          <Link
            to="/video-store"
            search={{ region: activeRegion }}
            className="absolute left-4 top-4 z-10 flex items-center gap-2 rounded-full bg-black/60 px-4 py-2 text-sm text-white/80 backdrop-blur hover:text-white"
          >
            <ArrowLeft className="size-4" />
            All stores
          </Link>
          <a
            href="https://www.justwatch.com"
            target="_blank"
            rel="noreferrer"
            className="absolute right-4 top-4 z-10 rounded-full bg-black/60 px-4 py-2 text-xs text-white/70 backdrop-blur hover:text-white"
          >
            Streaming data by JustWatch
          </a>
        </>
      }
    />
  )
}
