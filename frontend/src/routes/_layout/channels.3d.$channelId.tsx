// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link, redirect } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"
import { useCallback } from "react"
import { ChannelsService } from "@/client"
import { StoreScreen } from "@/components/Channels/Channel3D/StoreScreen"
import {
  fetchTitlePage,
  TITLE_PAGE,
} from "@/components/Channels/Channel3D/storeTitles"

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

  const fetchPage = useCallback(
    (offset: number) => fetchTitlePage(channelId, offset),
    [channelId],
  )

  return (
    <StoreScreen
      storeKey={channelId}
      storeName={channel?.name || "Video Store"}
      pageSize={TITLE_PAGE}
      fetchPage={fetchPage}
      emptyMessage="This channel has nothing on the shelves right now."
      back={
        <Link
          to="/channels/$channelId"
          params={{ channelId }}
          className="absolute left-4 top-4 z-10 flex items-center gap-2 rounded-full bg-black/60 px-4 py-2 text-sm text-white/80 backdrop-blur hover:text-white"
        >
          <ArrowLeft className="size-4" />
          Back to channel
        </Link>
      }
    />
  )
}
