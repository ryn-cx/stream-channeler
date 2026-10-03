// TODO: Validate
import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"
import { EpisodeLinkHistoryTable } from "@/components/AdminV2/EpisodeLinkHistoryTable"
import { Button } from "@/components/ui/button"

export const Route = createFileRoute("/_layout/admin-v2/episode-link-history")({
  component: AdminV2EpisodeLinkHistory,
  head: () => ({
    meta: [
      {
        title: "Episode Link History - Stream Channeler",
      },
    ],
  }),
})

// TODO: Validate
function AdminV2EpisodeLinkHistory() {
  return (
    <div className="flex flex-col gap-6">
      <div className="px-[4%] pt-4">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/admin-v2">
            <ArrowLeft />
            Back to Admin V2
          </Link>
        </Button>
      </div>
      <EpisodeLinkHistoryTable />
    </div>
  )
}
