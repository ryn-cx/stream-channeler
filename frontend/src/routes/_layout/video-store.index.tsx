// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { Loader2 } from "lucide-react"
import { VideoStoreService } from "@/client"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"

type VideoStoreSearch = { region?: string }

export const Route = createFileRoute("/_layout/video-store/")({
  component: VideoStoreIndex,
  validateSearch: (search: Record<string, unknown>): VideoStoreSearch => ({
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
function VideoStoreIndex() {
  const { region } = Route.useSearch()
  const navigate = Route.useNavigate()
  const activeRegion = region ?? "US"

  const { data: sources, isLoading } = useQuery({
    queryKey: ["video-store-sources"],
    queryFn: () => VideoStoreService.getStoreSources(),
    refetchOnWindowFocus: false,
  })

  const { data: regions } = useQuery({
    queryKey: ["video-store-regions"],
    queryFn: () => VideoStoreService.getStoreRegions(),
    refetchOnWindowFocus: false,
  })

  const { data: providers, isLoading: providersLoading } = useQuery({
    queryKey: ["video-store-watch-providers", activeRegion],
    queryFn: () =>
      VideoStoreService.getStoreWatchProviders({ region: activeRegion }),
    refetchOnWindowFocus: false,
  })

  return (
    <div className="px-[4%] py-6">
      <h1 className="text-2xl font-bold tracking-tight">Video Store</h1>
      <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
        Pick a website and see everything you can stream from it, laid out like
        an old school movie rental place from back in the day. Browse the
        shelves, pick up the cases and build a collection of your favorites
        before watching them. The whole store is a procedurally generated 3D
        environment, and every part of it is yours to customize.
      </p>

      <img
        src="/video-store.jpg"
        alt="Shelves of cases inside the 3D video store"
        className="mt-4 w-full rounded-lg border"
      />

      {isLoading && (
        <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
          {Array.from({ length: 12 }).map((_, index) => (
            <Skeleton key={index} className="h-20 w-full rounded-lg" />
          ))}
        </div>
      )}

      {sources && sources.length === 0 && (
        <div className="mt-10 flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="size-4" />
          No sources have any titles yet.
        </div>
      )}

      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
        {sources?.map((source) => (
          <Link
            key={source.id}
            to="/video-store/sources/$sourceId"
            params={{ sourceId: source.id }}
            className="flex items-center gap-3 rounded-lg border bg-card p-4 transition-colors hover:bg-accent"
          >
            {source.favicon_url ? (
              <img
                src={source.favicon_url}
                alt=""
                className="size-8 shrink-0 rounded object-contain"
                onError={(event) => {
                  event.currentTarget.style.visibility = "hidden"
                }}
              />
            ) : (
              <div className="size-8 shrink-0 rounded bg-muted" />
            )}
            <div className="min-w-0">
              <div className="truncate font-medium">{source.key}</div>
              <div className="truncate text-xs text-muted-foreground">
                {source.plugin_name} · {source.title_count.toLocaleString()}{" "}
                titles
              </div>
            </div>
          </Link>
        ))}
      </div>

      <div className="mt-12 flex flex-wrap items-end justify-between gap-4 border-t pt-6">
        <div>
          <h2 className="text-xl font-bold tracking-tight">
            Incomplete Stores
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Built from TMDB watch providers rather than an imported source, so
            the shelves only hold what TMDB knows is streaming.
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            Streaming availability data provided by{" "}
            <a
              href="https://www.justwatch.com"
              target="_blank"
              rel="noreferrer"
              className="font-medium underline underline-offset-2"
            >
              JustWatch
            </a>
            .
          </p>
        </div>
        <Select
          value={activeRegion}
          onValueChange={(value) =>
            navigate({ search: { region: value }, replace: true })
          }
        >
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Region" />
          </SelectTrigger>
          <SelectContent>
            {regions?.map((entry) => (
              <SelectItem key={entry.region} value={entry.region}>
                {entry.region} · {entry.title_count.toLocaleString()} titles
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {providersLoading && (
        <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, index) => (
            <Skeleton key={index} className="h-20 w-full rounded-lg" />
          ))}
        </div>
      )}

      {providers && providers.length === 0 && (
        <div className="mt-10 flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="size-4" />
          No watch providers carry anything in {activeRegion} yet.
        </div>
      )}

      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
        {providers?.map((provider) => (
          <Link
            key={provider.id}
            to="/video-store/providers/$watchProviderId"
            params={{ watchProviderId: provider.id }}
            search={{ region: activeRegion }}
            className="flex items-center gap-3 rounded-lg border bg-card p-4 transition-colors hover:bg-accent"
          >
            {provider.logo_url ? (
              <img
                src={provider.logo_url}
                alt=""
                className="size-8 shrink-0 rounded object-contain"
                onError={(event) => {
                  event.currentTarget.style.visibility = "hidden"
                }}
              />
            ) : (
              <div className="size-8 shrink-0 rounded bg-muted" />
            )}
            <div className="min-w-0">
              <div className="truncate font-medium">{provider.name}</div>
              <div className="truncate text-xs text-muted-foreground">
                {activeRegion} · {provider.title_count.toLocaleString()} titles
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
