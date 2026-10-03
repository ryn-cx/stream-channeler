// TODO: Validate
import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"
import { MismatchedTitlesTable } from "@/components/AdminV2/MismatchedTitlesTable"
import { Button } from "@/components/ui/button"

export const Route = createFileRoute("/_layout/admin-v2/mismatched-titles")({
  component: AdminV2MismatchedTitles,
  head: () => ({
    meta: [
      {
        title: "Mismatched Titles - Stream Channeler",
      },
    ],
  }),
})

// TODO: Validate
function AdminV2MismatchedTitles() {
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
      <MismatchedTitlesTable />
    </div>
  )
}
