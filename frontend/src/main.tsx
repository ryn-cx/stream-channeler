// TODO: Validate
import { removeOldestQuery } from "@tanstack/query-persist-client-core"
import { createSyncStoragePersister } from "@tanstack/query-sync-storage-persister"
import { MutationCache, QueryCache, QueryClient } from "@tanstack/react-query"
import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client"
import { createRouter, RouterProvider } from "@tanstack/react-router"
import { StrictMode } from "react"
import ReactDOM from "react-dom/client"
import { ApiError, OpenAPI } from "./client"
import { ThemeProvider } from "./components/theme-provider"
import { Toaster } from "./components/ui/sonner"
import "./index.css"
import { routeTree } from "./routeTree.gen"

OpenAPI.BASE = import.meta.env.VITE_API_URL
OpenAPI.TOKEN = async () => {
  return localStorage.getItem("access_token") || ""
}

// TODO: Validate
const handleApiError = (error: Error) => {
  if (error instanceof ApiError && [401, 403].includes(error.status)) {
    localStorage.removeItem("access_token")
    localStorage.removeItem("REACT_QUERY_OFFLINE_CACHE")
    window.location.href = "/login"
  }
}
const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: handleApiError,
  }),
  mutationCache: new MutationCache({
    onError: handleApiError,
  }),
})

let persistablePreviewHashes: string[] = []
let previewHashesComputedAt = -1

// TODO: Validate
const getPersistablePreviewHashes = () => {
  const now = Date.now()
  if (now !== previewHashesComputedAt) {
    previewHashesComputedAt = now
    persistablePreviewHashes = queryClient
      .getQueryCache()
      .getAll()
      .filter((query) => query.queryKey[0] === "episodes-preview")
      .sort((a, b) => b.state.dataUpdatedAt - a.state.dataUpdatedAt)
      .slice(0, 20)
      .map((query) => query.queryHash)
  }
  return persistablePreviewHashes
}

const persister = createSyncStoragePersister({
  storage: window.localStorage,
  retry: removeOldestQuery,
})

const isReload =
  (
    performance.getEntriesByType("navigation")[0] as
      | PerformanceNavigationTiming
      | undefined
  )?.type === "reload"

const router = createRouter({
  routeTree,
  scrollRestoration: ({ location }) =>
    location.state.mediaInformation === undefined,
})
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
      <PersistQueryClientProvider
        client={queryClient}
        persistOptions={{
          persister,
          maxAge: 60 * 60 * 1000,
          dehydrateOptions: {
            shouldDehydrateQuery: (query) => {
              if (query.state.status !== "success") return false
              if (query.queryKey[0] === "channels") return true
              if (query.queryKey[0] !== "episodes-preview") return false
              return getPersistablePreviewHashes().includes(query.queryHash)
            },
          },
        }}
        onSuccess={() => {
          if (isReload) queryClient.invalidateQueries()
        }}
      >
        <RouterProvider router={router} />
        <Toaster richColors closeButton />
      </PersistQueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
)
