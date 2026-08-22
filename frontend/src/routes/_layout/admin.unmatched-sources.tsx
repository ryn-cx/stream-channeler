// TODO: Validate
import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"
import { UnmatchedSourcesAdminTable } from "@/components/Admin/UnmatchedSourcesAdminTable"
import { Button } from "@/components/ui/button"

export const Route = createFileRoute("/_layout/admin/unmatched-sources")({
  component: AdminUnmatchedSources,
  head: () => ({
    meta: [
      {
        title: "Unmatched Sources - Stream Channeler",
      },
    ],
  }),
})

// TODO: Validate
function AdminUnmatchedSources() {
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
      <UnmatchedSourcesAdminTable title="Unmatched Sources" />
    </div>
  )
}
