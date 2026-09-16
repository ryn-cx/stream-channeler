// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link, redirect } from "@tanstack/react-router"
import { ArrowLeft, Loader2 } from "lucide-react"
import { useEffect, useState } from "react"
import { ChannelsService } from "@/client"
import type { StoreTitle } from "@/components/Channels/Channel3D/caseTexture"
import {
  fetchTitlePage,
  TITLE_PAGE,
} from "@/components/Channels/Channel3D/storeTitles"
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
  const [stock, setStock] = useState<{
    capacity: number
    titles: StoreTitle[]
  } | null>(null)

  const { data: channel } = useQuery({
    queryKey: ["channels", channelId],
    queryFn: () => ChannelsService.getChannel({ channelId }),
    refetchOnWindowFocus: false,
  })

  useEffect(() => {
    let cancelled = false
    const shelved = new Map<string, StoreTitle>()

    // TODO: Validate
    const shelve = (page: { titles: StoreTitle[]; total: number }) => {
      for (const title of page.titles) {
        if (!shelved.has(title.id)) shelved.set(title.id, title)
      }
      setStock({ capacity: page.total, titles: [...shelved.values()] })
    }

    // TODO: Validate
    const stockShelves = async () => {
      const first = await fetchTitlePage(channelId, 0)
      if (cancelled) return
      shelve(first)

      const offsets: number[] = []
      for (
        let offset = TITLE_PAGE;
        offset < first.total;
        offset += TITLE_PAGE
      ) {
        offsets.push(offset)
      }
      while (offsets.length > 0 && !cancelled) {
        const batch = offsets.splice(0, 4)
        const pages = await Promise.all(
          batch.map((offset) => fetchTitlePage(channelId, offset)),
        )
        if (cancelled) return
        for (const page of pages) shelve(page)
      }
    }

    stockShelves()
    return () => {
      cancelled = true
    }
  }, [channelId])

  // TODO: Validate
  const onActivate = (title: StoreTitle) => {
    if (title.url) window.open(title.url, "_blank", "noopener,noreferrer")
  }

  return (
    <div className="fixed inset-0 z-50 bg-black">
      {stock && stock.titles.length > 0 ? (
        <VideoStoreCanvas
          titles={stock.titles}
          capacity={stock.capacity}
          channelName={channel?.name || "Video Store"}
          onActivate={onActivate}
        />
      ) : (
        <div className="flex size-full flex-col items-center justify-center gap-3 text-white/70">
          {stock ? (
            <span>This channel has nothing on the shelves right now.</span>
          ) : (
            <>
              <Loader2 className="size-6 animate-spin" />
              <span className="text-sm">Unlocking the store…</span>
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
