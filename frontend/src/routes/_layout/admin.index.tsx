// TODO: Validate
import { createFileRoute, Link } from "@tanstack/react-router"
import {
  Clapperboard,
  Flag,
  Layers,
  Link2,
  ListOrdered,
  Radio,
  Tv,
  Unlock,
  Users,
} from "lucide-react"
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

// TODO: Validate
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
        <Link to="/admin/reports" className="block">
          <Card className="h-full transition-colors hover:border-primary">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Flag className="size-5" />
                All Issue Reports
              </CardTitle>
              <CardDescription>
                Every issue reported against an episode, season or show, newest
                first.
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
        <Link to="/admin/episode-reports" className="block">
          <Card className="h-full transition-colors hover:border-primary">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clapperboard className="size-5" />
                Episode Issue Reports
              </CardTitle>
              <CardDescription>
                Each reported episode once, with how many issues were reported
                against it and what they say.
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
        <Link to="/admin/season-reports" className="block">
          <Card className="h-full transition-colors hover:border-primary">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Layers className="size-5" />
                Season Issue Reports
              </CardTitle>
              <CardDescription>
                Each reported season once, with how many issues were reported
                against it and what they say.
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
        <Link to="/admin/show-reports" className="block">
          <Card className="h-full transition-colors hover:border-primary">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Tv className="size-5" />
                Show Issue Reports
              </CardTitle>
              <CardDescription>
                Each reported title once, with how many issues were reported
                against it and what they say.
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
        <Link to="/admin/tmdb-matches" className="block">
          <Card className="h-full transition-colors hover:border-primary">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Link2 className="size-5" />
                TMDB Matches
              </CardTitle>
              <CardDescription>
                Every episode no TMDB record was found for, beside the closest
                TMDB episode, to be approved or replaced by hand.
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
        <Link to="/admin/unlocked-episodes" className="block">
          <Card className="h-full transition-colors hover:border-primary">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Unlock className="size-5" />
                Unlocked Episodes
              </CardTitle>
              <CardDescription>
                Every episode whose TMDB link nobody has settled, matched or
                not. A name shown in red is one TMDB agrees with, which means
                the two disagree about the number.
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
