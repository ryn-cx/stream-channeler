// TODO: Validate
import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"
import { UnlockedEpisodesAdminTable } from "@/components/Admin/UnlockedEpisodesAdminTable"
import { Button } from "@/components/ui/button"

export const Route = createFileRoute("/_layout/admin/unlocked-episodes")({
  component: AdminUnlockedEpisodes,
  head: () => ({
    meta: [
      {
        title: "Unlocked Episodes - Stream Channeler",
      },
    ],
  }),
})

// TODO: Validate
function AdminUnlockedEpisodes() {
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
      <UnlockedEpisodesAdminTable />
    </div>
  )
}
