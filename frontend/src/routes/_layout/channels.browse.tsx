// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Globe,
} from "lucide-react"
import { useState } from "react"
import { ChannelsService } from "@/client"
import { ChannelsBrowse } from "@/components/Channels/ChannelList/ChannelsBrowse"
import { EmptyState } from "@/components/Common/EmptyState"
import { PageHeader } from "@/components/Common/PageHeader"
import PendingChannelList from "@/components/Pending/PendingChannelList"
import { Button } from "@/components/ui/button"
import { isLoggedIn } from "@/hooks/useAuth"

const CHANNELS_PER_PAGE = 10

function getPublicChannelsQueryOptions(page: number) {
  return {
    queryFn: () =>
      ChannelsService.getPublicChannels({
        offset: page * CHANNELS_PER_PAGE,
        limit: CHANNELS_PER_PAGE,
      }),
    queryKey: ["channels", "public", page],
    refetchOnWindowFocus: false,
    placeholderData: (previousData: any) => previousData,
  }
}

export const Route = createFileRoute("/_layout/channels/browse")({
  component: PublicChannels,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [
      {
        title: "Public Channels - Stream Channeler",
      },
    ],
  }),
})

function PublicChannelsContent() {
  // Zero-based page index, matching the offset/limit query params.
  const [page, setPage] = useState(0)
  const { data, isPlaceholderData } = useQuery(
    getPublicChannelsQueryOptions(page),
  )

  if (!data) return <PendingChannelList />

  const pageCount = Math.max(1, Math.ceil(data.count / CHANNELS_PER_PAGE))
  const canPreviousPage = page > 0
  const canNextPage = page < pageCount - 1

  return (
    <div
      className={
        isPlaceholderData
          ? "opacity-60 transition-opacity duration-200"
          : undefined
      }
    >
      <PageHeader title="Public Channels" />

      {data.count === 0 ? (
        <EmptyState
          icon={Globe}
          title="No public channels yet"
          description="Public channels with a score of 1 or higher will show up here."
        />
      ) : (
        <>
          <ChannelsBrowse channels={data.data} readOnly />

          <div className="flex items-center justify-center gap-x-6 pb-8">
            <div className="flex items-center gap-x-1 text-sm text-muted-foreground">
              <span>Page</span>
              <span className="font-medium text-foreground">{page + 1}</span>
              <span>of</span>
              <span className="font-medium text-foreground">{pageCount}</span>
            </div>

            <div className="flex items-center gap-x-1">
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => setPage(0)}
                disabled={!canPreviousPage}
              >
                <span className="sr-only">Go to first page</span>
                <ChevronsLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => setPage((current) => current - 1)}
                disabled={!canPreviousPage}
              >
                <span className="sr-only">Go to previous page</span>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => setPage((current) => current + 1)}
                disabled={!canNextPage}
              >
                <span className="sr-only">Go to next page</span>
                <ChevronRight className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => setPage(pageCount - 1)}
                disabled={!canNextPage}
              >
                <span className="sr-only">Go to last page</span>
                <ChevronsRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function PublicChannels() {
  return (
    <div className="flex flex-col gap-6">
      <PublicChannelsContent />
    </div>
  )
}
