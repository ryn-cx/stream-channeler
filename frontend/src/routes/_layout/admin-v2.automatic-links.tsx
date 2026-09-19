// TODO: Validate
import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"
import { AutomaticLinkGroupsTable } from "@/components/AdminV2/AutomaticLinkGroupsTable"
import { Button } from "@/components/ui/button"

export const Route = createFileRoute("/_layout/admin-v2/automatic-links")({
  component: AdminV2AutomaticLinks,
  head: () => ({
    meta: [
      {
        title: "Reset Automatic Links - Stream Channeler",
      },
    ],
  }),
})

// TODO: Validate
function AdminV2AutomaticLinks() {
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
      <AutomaticLinkGroupsTable />
    </div>
  )
}
