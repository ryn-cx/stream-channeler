// TODO: Validate
import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"
import { TmdbMatchesAdminTable } from "@/components/Admin/TmdbMatchesAdminTable"
import { Button } from "@/components/ui/button"

export const Route = createFileRoute("/_layout/admin/tmdb-matches")({
  component: AdminTmdbMatches,
  head: () => ({
    meta: [
      {
        title: "TMDB Matches - Stream Channeler",
      },
    ],
  }),
})

// TODO: Validate
function AdminTmdbMatches() {
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
      <TmdbMatchesAdminTable />
    </div>
  )
}
