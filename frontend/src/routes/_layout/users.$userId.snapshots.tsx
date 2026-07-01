// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { Globe } from "lucide-react"

import { UsersService } from "@/client"
import { EmptyState } from "@/components/Common/EmptyState"
import { PageHeader } from "@/components/Common/PageHeader"
import PendingSnapshots from "@/components/Pending/PendingSnapshots"
import { SnapshotsBrowse } from "@/components/Snapshots/SnapshotList/SnapshotsBrowse"
import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/users/$userId/snapshots")({
  component: UserSnapshots,
  head: () => ({
    meta: [{ title: "User Snapshots - Stream Channeler" }],
  }),
})

function UserSnapshots() {
  const { userId } = Route.useParams()
  const { user } = useAuth()
  const isOwner = user?.id === userId
  const { data } = useQuery({
    queryKey: ["snapshots", "public", "by-user", userId],
    queryFn: () => UsersService.getUserPublicSnapshots({ userId }),
  })

  if (!data) return <PendingSnapshots />

  const firstSnapshot = data.data[0]
  const username = firstSnapshot
    ? firstSnapshot.username || "Unnamed User"
    : "this user"

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={`Snapshots by ${username}`} />
      {isOwner && (
        <p className="-mt-4 px-[4%] text-sm text-muted-foreground">
          This page lists only your public snapshots. See{" "}
          <Link to="/snapshots" className="underline hover:text-foreground">
            My Snapshots
          </Link>{" "}
          for all of your snapshots.
        </p>
      )}
      {data.count === 0 ? (
        <EmptyState
          icon={Globe}
          title="No public snapshots"
          description="This user has no public snapshots yet."
        />
      ) : (
        <SnapshotsBrowse snapshots={data.data} readOnly showCreatedBy={false} />
      )}
    </div>
  )
}
