// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link, redirect } from "@tanstack/react-router"
import { ArrowLeft, Loader2 } from "lucide-react"
import { useRef } from "react"
import { ChannelsService } from "@/client"
import type { StoreTitle } from "@/components/Channels/Channel3D/caseTexture"
import { fetchStoreTitles } from "@/components/Channels/Channel3D/storeTitles"
import { VideoStoreCanvas } from "@/components/Channels/Channel3D/VideoStoreCanvas"

export const Route = createFileRoute("/_layout/channels/3d/$channelId")({
  component: Channel3D,
  // TODO: Validate
  beforeLoad: async ({ params }) => {
    try {
      await ChannelsService.getChannel({ channelId: params.channelId })
    } catch (error: any) {
      if (error?.status === 401 || error?.status === 403) {
        throw redirect({ to: "/" })
      }
      throw error
    }
  },
  head: () => ({
    meta: [{ title: "Video Store - Stream Channeler" }],
  }),
})

// TODO: Validate
function Channel3D() {
  const { channelId } = Route.useParams()

  const { data: channel } = useQuery({
    queryKey: ["channels", channelId],
    queryFn: () => ChannelsService.getChannel({ channelId }),
    refetchOnWindowFocus: false,
  })

  const { data: titles } = useQuery({
    queryKey: ["channel-store-titles", channelId],
    queryFn: () => fetchStoreTitles(channelId),
    refetchOnWindowFocus: false,
  })

  const shelved = useRef<StoreTitle[] | null>(null)
  if (titles && !shelved.current) shelved.current = titles

  // TODO: Validate
  const onActivate = (title: StoreTitle) => {
    if (title.url) window.open(title.url, "_blank", "noopener,noreferrer")
  }

  return (
    <div className="fixed inset-0 z-50 bg-black">
      {shelved.current && shelved.current.length > 0 ? (
        <VideoStoreCanvas
          titles={shelved.current}
          channelName={channel?.name || "Video Store"}
          onActivate={onActivate}
        />
      ) : (
        <div className="flex size-full flex-col items-center justify-center gap-3 text-white/70">
          {shelved.current ? (
            <span>This channel has nothing on the shelves right now.</span>
          ) : (
            <>
              <Loader2 className="size-6 animate-spin" />
              <span className="text-sm">Stocking the shelves…</span>
            </>
          )}
        </div>
      )}

      <Link
        to="/channels/$channelId"
        params={{ channelId }}
        className="absolute left-4 top-4 z-10 flex items-center gap-2 rounded-full bg-black/60 px-4 py-2 text-sm text-white/80 backdrop-blur hover:text-white"
      >
        <ArrowLeft className="size-4" />
        Back to channel
      </Link>
    </div>
  )
}
