// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Globe,
} from "lucide-react"
import { useState } from "react"
import { SnapshotsService } from "@/client"
import { EmptyState } from "@/components/Common/EmptyState"
import { PageHeader } from "@/components/Common/PageHeader"
import PendingSnapshots from "@/components/Pending/PendingSnapshots"
import { SnapshotsBrowse } from "@/components/Snapshots/SnapshotList/SnapshotsBrowse"
import { Button } from "@/components/ui/button"

const SNAPSHOTS_PER_PAGE = 10

function getPublicSnapshotsQueryOptions(page: number) {
  return {
    queryFn: () =>
      SnapshotsService.getPublicSnapshots({
        offset: page * SNAPSHOTS_PER_PAGE,
        limit: SNAPSHOTS_PER_PAGE,
      }),
    queryKey: ["snapshots", "public", page],
    refetchOnWindowFocus: false,
    placeholderData: (previousData: any) => previousData,
  }
}

export const Route = createFileRoute("/_layout/snapshots/browse")({
  component: PublicSnapshots,
  head: () => ({
    meta: [
      {
        title: "Public Snapshots - Stream Channeler",
      },
    ],
  }),
})

function PublicSnapshotsContent() {
  // Zero-based page index, matching the offset/limit query params.
  const [page, setPage] = useState(0)
  const { data, isPlaceholderData } = useQuery(
    getPublicSnapshotsQueryOptions(page),
  )

  if (!data) return <PendingSnapshots />

  const pageCount = Math.max(1, Math.ceil(data.count / SNAPSHOTS_PER_PAGE))
  const canPreviousPage = page > 0
  const canNextPage = page < pageCount - 1

  return (
    <div
      className={
        isPlaceholderData
          ? "opacity-60 transition-opacity duration-200"
          : undefined
      }
    >
      <PageHeader title="Public Snapshots" />

      {data.count === 0 ? (
        <EmptyState
          icon={Globe}
          title="No public snapshots yet"
          description="Public snapshots with a score of 1 or higher will show up here."
        />
      ) : (
        <>
          <SnapshotsBrowse snapshots={data.data} readOnly />

          <div className="flex items-center justify-center gap-x-6 pb-8">
            <div className="flex items-center gap-x-1 text-sm text-muted-foreground">
              <span>Page</span>
              <span className="font-medium text-foreground">{page + 1}</span>
              <span>of</span>
              <span className="font-medium text-foreground">{pageCount}</span>
            </div>

            <div className="flex items-center gap-x-1">
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => setPage(0)}
                disabled={!canPreviousPage}
              >
                <span className="sr-only">Go to first page</span>
                <ChevronsLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => setPage((current) => current - 1)}
                disabled={!canPreviousPage}
              >
                <span className="sr-only">Go to previous page</span>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => setPage((current) => current + 1)}
                disabled={!canNextPage}
              >
                <span className="sr-only">Go to next page</span>
                <ChevronRight className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => setPage(pageCount - 1)}
                disabled={!canNextPage}
              >
                <span className="sr-only">Go to last page</span>
                <ChevronsRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function PublicSnapshots() {
  return (
    <div className="flex flex-col gap-6">
      <PublicSnapshotsContent />
    </div>
  )
}
