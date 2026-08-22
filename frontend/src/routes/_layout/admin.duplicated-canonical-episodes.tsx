// TODO: Validate
import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"
import { DuplicatedCanonicalEpisodesAdminTable } from "@/components/Admin/DuplicatedCanonicalEpisodesAdminTable"
import { Button } from "@/components/ui/button"

export const Route = createFileRoute(
  "/_layout/admin/duplicated-canonical-episodes",
)({
  component: AdminDuplicatedCanonicalEpisodes,
  head: () => ({
    meta: [
      {
        title: "Duplicated Canonical Episodes - Stream Channeler",
      },
    ],
  }),
})

// TODO: Validate
function AdminDuplicatedCanonicalEpisodes() {
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
      <DuplicatedCanonicalEpisodesAdminTable />
    </div>
  )
}
