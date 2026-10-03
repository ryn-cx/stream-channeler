// TODO: Validate
import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"
import { UserActionsTable } from "@/components/AdminV2/UserActionsTable"
import { Button } from "@/components/ui/button"

export const Route = createFileRoute("/_layout/admin-v2/user-actions")({
  component: AdminV2UserActions,
  head: () => ({
    meta: [
      {
        title: "User Actions - Stream Channeler",
      },
    ],
  }),
})

// TODO: Validate
function AdminV2UserActions() {
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
      <UserActionsTable />
    </div>
  )
}
