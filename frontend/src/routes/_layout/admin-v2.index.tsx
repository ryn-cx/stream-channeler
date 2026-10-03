// TODO: Validate
import { createFileRoute, Link } from "@tanstack/react-router"
import {
  Bot,
  Flag,
  History,
  Link2,
  SearchX,
  Tv,
  Unlink,
  UserSearch,
} from "lucide-react"
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
              <CardDescription>Link episodes to TMDB</CardDescription>
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
                Link TMDB titles to sources that are missing
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
        <Link to="/admin-v2/mismatched-titles" className="block">
          <Card className="h-full transition-colors hover:border-primary">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <SearchX className="size-5" />
                Mismatched Titles
              </CardTitle>
              <CardDescription>
                Unverified titles whose name or year differs from the TMDB title
                they are linked to
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
        <Link to="/admin-v2/unlinked-titles" className="block">
          <Card className="h-full transition-colors hover:border-primary">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Unlink className="size-5" />
                Unlinked Titles
              </CardTitle>
              <CardDescription>
                Titles that are not linked to a TMDB title
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
        <Link to="/admin-v2/episode-link-history" className="block">
          <Card className="h-full transition-colors hover:border-primary">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <History className="size-5" />
                Episode Link History
              </CardTitle>
              <CardDescription>
                Every episode linked or ignored by hand, newest first
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
        <Link to="/admin-v2/title-link-history" className="block">
          <Card className="h-full transition-colors hover:border-primary">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <History className="size-5" />
                Title Link History
              </CardTitle>
              <CardDescription>
                Every title linked, ignored or settled as absent by hand, newest
                first
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
        <Link to="/admin-v2/reports" className="block">
          <Card className="h-full transition-colors hover:border-primary">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Flag className="size-5" />
                Issue Reports
              </CardTitle>
              <CardDescription>
                Review what users have reported and act on suggested matches
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
        <Link to="/admin-v2/user-actions" className="block">
          <Card className="h-full transition-colors hover:border-primary">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <UserSearch className="size-5" />
                User Actions
              </CardTitle>
              <CardDescription>
                Searches, imports, reports and other actions users have taken,
                newest first
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
            </CardHeader>
          </Card>
        </Link>
      </div>
    </div>
  )
}
