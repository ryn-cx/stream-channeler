// TODO: Validate
import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"
import { UnlinkedTitlesTable } from "@/components/AdminV2/UnlinkedTitlesTable"
import { Button } from "@/components/ui/button"

export const Route = createFileRoute("/_layout/admin-v2/unlinked-titles")({
  component: AdminV2UnlinkedTitles,
  head: () => ({
    meta: [
      {
        title: "Unlinked Titles - Stream Channeler",
      },
    ],
  }),
})

// TODO: Validate
function AdminV2UnlinkedTitles() {
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
      <UnlinkedTitlesTable />
    </div>
  )
}
