// TODO: Validate
import type { PaginationState } from "@tanstack/react-table"
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react"
import type { Dispatch, SetStateAction } from "react"
import { useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

// Each browse row renders a full episode carousel, so browse pages at most 100
// channels at a time even though the table view allows more.
export const BROWSE_PAGE_SIZES = [10, 25, 50, 100]
export const MAX_BROWSE_PAGE_SIZE = 100
export const DEFAULT_BROWSE_PAGE_SIZE = 10

function readStoredBrowsePageSize(storageKey: string): number {
  const stored = localStorage.getItem(storageKey)
  if (stored !== null) {
    const parsed = Number(stored)
    if (Number.isFinite(parsed) && parsed > 0) {
      return Math.min(parsed, MAX_BROWSE_PAGE_SIZE)
    }
  }
  return DEFAULT_BROWSE_PAGE_SIZE
}

// Persists the browse page size to localStorage so "per page" survives reloads
// and navigation, mirroring how the table view persists its own page size. The
// page index stays ephemeral so a fresh visit always starts on the first page.
export function useBrowsePagination(
  storageKey: string,
): [PaginationState, Dispatch<SetStateAction<PaginationState>>] {
  const [pagination, setPagination] = useState<PaginationState>(() => ({
    pageIndex: 0,
    pageSize: readStoredBrowsePageSize(storageKey),
  }))

  useEffect(() => {
    localStorage.setItem(storageKey, `${pagination.pageSize}`)
  }, [storageKey, pagination.pageSize])

  return [pagination, setPagination]
}

export function BrowsePagination({
  pagination,
  onPaginationChange,
  rowCount,
  itemLabel = "Channels",
}: {
  pagination: PaginationState
  onPaginationChange: (pagination: PaginationState) => void
  rowCount: number
  itemLabel?: string
}) {
  const pageCount = Math.max(1, Math.ceil(rowCount / pagination.pageSize))
  const canPreviousPage = pagination.pageIndex > 0
  const canNextPage = pagination.pageIndex < pageCount - 1

  const setPageIndex = (pageIndex: number) =>
    onPaginationChange({ ...pagination, pageIndex })

  return (
    <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 pb-8">
      <div className="flex items-center gap-x-2">
        <p className="text-sm text-muted-foreground">{itemLabel} per page</p>
        <Select
          value={`${pagination.pageSize}`}
          onValueChange={(value) =>
            onPaginationChange({ pageIndex: 0, pageSize: Number(value) })
          }
        >
          <SelectTrigger
            className="h-8 w-[70px]"
            aria-label={`${itemLabel} per page`}
          >
            <SelectValue placeholder={pagination.pageSize} />
          </SelectTrigger>
          <SelectContent side="top">
            {BROWSE_PAGE_SIZES.map((size) => (
              <SelectItem key={size} value={`${size}`}>
                {size}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex items-center gap-x-1 text-sm text-muted-foreground">
        <span>Page</span>
        <span className="font-medium text-foreground">
          {pagination.pageIndex + 1}
        </span>
        <span>of</span>
        <span className="font-medium text-foreground">{pageCount}</span>
      </div>

      <div className="flex items-center gap-x-1">
        <Button
          variant="outline"
          size="sm"
          className="h-8 w-8 p-0"
          onClick={() => setPageIndex(0)}
          disabled={!canPreviousPage}
        >
          <span className="sr-only">Go to first page</span>
          <ChevronsLeft className="h-4 w-4" />
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="h-8 w-8 p-0"
          onClick={() => setPageIndex(pagination.pageIndex - 1)}
          disabled={!canPreviousPage}
        >
          <span className="sr-only">Go to previous page</span>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="h-8 w-8 p-0"
          onClick={() => setPageIndex(pagination.pageIndex + 1)}
          disabled={!canNextPage}
        >
          <span className="sr-only">Go to next page</span>
          <ChevronRight className="h-4 w-4" />
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="h-8 w-8 p-0"
          onClick={() => setPageIndex(pageCount - 1)}
          disabled={!canNextPage}
        >
          <span className="sr-only">Go to last page</span>
          <ChevronsRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
