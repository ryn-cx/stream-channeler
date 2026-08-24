// TODO: Validate
import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"
import { UnvalidatedShowsAdminTable } from "@/components/Admin/UnvalidatedShowsAdminTable"
import { Button } from "@/components/ui/button"

export const Route = createFileRoute("/_layout/admin/unvalidated-shows")({
  component: AdminUnvalidatedShows,
  head: () => ({
    meta: [
      {
        title: "Unvalidated Shows - Stream Channeler",
      },
    ],
  }),
})

// TODO: Validate
function AdminUnvalidatedShows() {
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
      <UnvalidatedShowsAdminTable />
    </div>
  )
}
