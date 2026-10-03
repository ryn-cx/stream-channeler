// TODO: Validate
import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"
import { ChannelQueuesAdminTable } from "@/components/Admin/ChannelQueuesAdminTable"
import { Button } from "@/components/ui/button"

export const Route = createFileRoute("/_layout/admin/channel-queues")({
  component: AdminChannelQueues,
  head: () => ({
    meta: [
      {
        title: "Admin Channel Queues - Stream Channeler",
      },
    ],
  }),
})

// TODO: Validate
function AdminChannelQueues() {
  return (
    <div className="flex flex-col gap-6">
      <div className="px-[4%] pt-4">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/admin">
            <ArrowLeft />
            Back to Admin
          </Link>
        </Button>
      </div>
      <ChannelQueuesAdminTable />
    </div>
  )
}
