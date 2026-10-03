// TODO: Validate
import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"
import { UnvalidatedTitlesAdminTable } from "@/components/Admin/UnvalidatedTitlesAdminTable"
import { Button } from "@/components/ui/button"

export const Route = createFileRoute("/_layout/admin/unvalidated-titles")({
  component: AdminUnvalidatedTitles,
  head: () => ({
    meta: [
      {
        title: "Unvalidated Titles - Stream Channeler",
      },
    ],
  }),
})

// TODO: Validate
function AdminUnvalidatedTitles() {
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
      <UnvalidatedTitlesAdminTable />
    </div>
  )
}
