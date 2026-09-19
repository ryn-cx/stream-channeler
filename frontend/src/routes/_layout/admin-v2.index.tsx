// TODO: Validate
import { createFileRoute, Link } from "@tanstack/react-router"
import { Bot, Link2, Link2Off, Tv } from "lucide-react"
import { PageHeader } from "@/components/Common/PageHeader"
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

export const Route = createFileRoute("/_layout/admin-v2/")({
  component: AdminV2Index,
  head: () => ({
    meta: [
      {
        title: "Admin V2 - Stream Channeler",
      },
    ],
  }),
})

// TODO: Validate
function AdminV2Index() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Admin V2" />
      <div className="grid grid-cols-1 gap-4 px-[4%] sm:grid-cols-2">
        <Link to="/admin-v2/link-episode" className="block">
          <Card className="h-full transition-colors hover:border-primary">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Link2 className="size-5" />
                Link Episode
              </CardTitle>
              <CardDescription>
                Every episode still waiting on a TMDB episode, either across the
                whole library or only the ones a user's channel holds.
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
        <Link to="/admin-v2/link-title" className="block">
          <Card className="h-full transition-colors hover:border-primary">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Tv className="size-5" />
                Link Title
              </CardTitle>
              <CardDescription>
                Every title TMDB holds that no website's row stands for, with
                the address of a page carrying it to be given by hand.
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
        <Link to="/admin-v2/automatic-links" className="block">
          <Card className="h-full transition-colors hover:border-primary">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Link2Off className="size-5" />
                Reset Automatic Links
              </CardTitle>
              <CardDescription>
                Titles whose every TMDB link was made automatically and never
                verified, counted by plugin or by source, with a way to drop
                those links so they are matched again.
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
        <Link to="/admin-v2/automatic-channels" className="block">
          <Card className="h-full transition-colors hover:border-primary">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bot className="size-5" />
                Manage Automatic Channels
              </CardTitle>
              <CardDescription>
                The users a source writes its channels as, and a way to delete
                every channel one of them owns.
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
      </div>
    </div>
  )
}
