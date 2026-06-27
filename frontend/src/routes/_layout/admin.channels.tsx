// TODO: Validate
import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"
import { ChannelsAdminTable } from "@/components/Admin/ChannelsAdminTable"
import { Button } from "@/components/ui/button"

export const Route = createFileRoute("/_layout/admin/channels")({
  component: AdminChannels,
  head: () => ({
    meta: [
      {
        title: "Admin Channels - Stream Channeler",
      },
    ],
  }),
})

function AdminChannels() {
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
      <ChannelsAdminTable />
    </div>
  )
}
