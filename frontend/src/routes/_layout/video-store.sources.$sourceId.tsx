// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"
import { useCallback } from "react"
import { VideoStoreService } from "@/client"
import { StoreScreen } from "@/components/Channels/Channel3D/StoreScreen"
import { fetchSourceTitles } from "@/components/Channels/Channel3D/sourceTitles"

export const Route = createFileRoute("/_layout/video-store/sources/$sourceId")({
  component: SourceStore,
  head: () => ({
    meta: [{ title: "Video Store - Stream Channeler" }],
  }),
})

// TODO: Validate
function SourceStore() {
  const { sourceId } = Route.useParams()

  const { data: sources } = useQuery({
    queryKey: ["video-store-sources"],
    queryFn: () => VideoStoreService.getStoreSources(),
    refetchOnWindowFocus: false,
  })
  const source = sources?.find((entry) => entry.id === sourceId)

  const fetchStock = useCallback(() => fetchSourceTitles(sourceId), [sourceId])

  return (
    <StoreScreen
      storeKey={sourceId}
      storeName={source?.key || "Video Store"}
      fetchStock={fetchStock}
      emptyMessage="This source has nothing on the shelves right now."
      back={
        <Link
          to="/video-store"
          className="absolute left-4 top-4 z-10 flex items-center gap-2 rounded-full bg-black/60 px-4 py-2 text-sm text-white/80 backdrop-blur hover:text-white"
        >
          <ArrowLeft className="size-4" />
          All stores
        </Link>
      }
    />
  )
}
