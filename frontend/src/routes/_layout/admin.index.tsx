// TODO: Validate
import { createFileRoute, Link } from "@tanstack/react-router"
import { ListOrdered, Radio, Users } from "lucide-react"
import { PageHeader } from "@/components/Common/PageHeader"
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

export const Route = createFileRoute("/_layout/admin/")({
  component: AdminIndex,
  head: () => ({
    meta: [
      {
        title: "Admin - Stream Channeler",
      },
    ],
  }),
})

function AdminIndex() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Admin" />
      <div className="grid grid-cols-1 gap-4 px-[4%] sm:grid-cols-2">
        <Link to="/admin/channels" className="block">
          <Card className="h-full transition-colors hover:border-primary">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Radio className="size-5" />
                Channels
              </CardTitle>
              <CardDescription>
                View, approve, and edit every channel on the site, or filter to
                a single user's channels.
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
        <Link to="/admin/channel-queues" className="block">
          <Card className="h-full transition-colors hover:border-primary">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ListOrdered className="size-5" />
                Channel Queues
              </CardTitle>
              <CardDescription>
                View and edit every channel's import queue, or filter to a
                single user's queues.
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
        <Link to="/admin/users" className="block">
          <Card className="h-full transition-colors hover:border-primary">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="size-5" />
                Users
              </CardTitle>
              <CardDescription>
                Manage all user accounts, including roles and access.
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
      </div>
    </div>
  )
}
