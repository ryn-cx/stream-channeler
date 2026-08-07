// TODO: Validate
import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"
import { IssueReportsAdminTable } from "@/components/Admin/IssueReportsAdminTable"
import { Button } from "@/components/ui/button"

export const Route = createFileRoute("/_layout/admin/reports")({
  component: AdminReports,
  head: () => ({
    meta: [
      {
        title: "All Issue Reports - Stream Channeler",
      },
    ],
  }),
})

function AdminReports() {
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
      <IssueReportsAdminTable title="All Issue Reports" />
    </div>
  )
}
