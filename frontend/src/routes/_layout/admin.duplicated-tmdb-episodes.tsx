// TODO: Validate
import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"
import { DuplicatedTmdbEpisodesAdminTable } from "@/components/Admin/DuplicatedTmdbEpisodesAdminTable"
import { Button } from "@/components/ui/button"

export const Route = createFileRoute("/_layout/admin/duplicated-tmdb-episodes")(
  {
    component: AdminDuplicatedTmdbEpisodes,
    head: () => ({
      meta: [
        {
          title: "Duplicated TMDB Episodes - Stream Channeler",
        },
      ],
    }),
  },
)

// TODO: Validate
function AdminDuplicatedTmdbEpisodes() {
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
      <DuplicatedTmdbEpisodesAdminTable />
    </div>
  )
}
