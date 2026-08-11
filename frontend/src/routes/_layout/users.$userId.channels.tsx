// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { Globe } from "lucide-react"

import { UsersService } from "@/client"
import { ChannelsBrowse } from "@/components/Channels/ChannelList/ChannelsBrowse"
import { EmptyState } from "@/components/Common/EmptyState"
import { PageHeader } from "@/components/Common/PageHeader"
import PendingChannelList from "@/components/Pending/PendingChannelList"
import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/users/$userId/channels")({
  component: UserChannels,
  head: () => ({
    meta: [{ title: "User Channels - Stream Channeler" }],
  }),
})

// TODO: Validate
function UserChannels() {
  const { userId } = Route.useParams()
  const { user } = useAuth()
  const isOwner = user?.id === userId
  const { data } = useQuery({
    queryKey: ["channels", "public", "by-user", userId],
    queryFn: () => UsersService.getUserPublicChannels({ userId }),
  })

  if (!data) return <PendingChannelList />

  const firstChannel = data.data[0]
  const username = firstChannel?.username ?? "this user"

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={`Channels by ${username}`} />
      {isOwner && (
        <p className="-mt-4 px-[4%] text-sm text-muted-foreground">
          This page lists only your public channels. See{" "}
          <Link
            to="/channels"
            search={{ view: "owned" }}
            className="underline hover:text-foreground"
          >
            My Channels
          </Link>{" "}
          for all of your channels.
        </p>
      )}
      {data.count === 0 ? (
        <EmptyState
          icon={Globe}
          title="No public channels"
          description="This user has no public channels yet."
        />
      ) : (
        <ChannelsBrowse channels={data.data} readOnly showCreatedBy={false} />
      )}
    </div>
  )
}
