// TODO: Validate
import type { PaginationState } from "@tanstack/react-table"
import { Search } from "lucide-react"
import { useMemo, useState } from "react"

import type { ChannelListOutput } from "@/client"
import {
  type BrowseChannel,
  ChannelsBrowse,
  sortChannelsByNumber,
} from "@/components/Channels/ChannelList/ChannelsBrowse"
import { BrowsePagination } from "@/components/Common/BrowsePagination"
import { Input } from "@/components/ui/input"

// Favorites carry the viewer's private name, which is what they see and search on.
// TODO: Validate
function channelSearchName(channel: BrowseChannel): string {
  return (channel as ChannelListOutput).custom_name ?? channel.name ?? ""
}

interface ChannelsBrowseSectionProps {
  rows: BrowseChannel[]
  isServer: boolean
  serverRowCount: number
  pagination: PaginationState
  onPaginationChange: (pagination: PaginationState) => void
  sortByNumber?: boolean
  readOnly?: boolean
  personalizable?: boolean
  showCreatedBy?: boolean
  showChannelNumber?: boolean
}

// The browse (visual) view for a channel list: an optional name search, the
// channel rows, and pagination. Sort, search, and paging run client-side, so the
// name filter and the channel-number sort are only applied when the whole list is
// loaded (not server-paginated).
// TODO: Validate
export function ChannelsBrowseSection({
  rows,
  isServer,
  serverRowCount,
  pagination,
  onPaginationChange,
  sortByNumber = false,
  readOnly,
  personalizable,
  showCreatedBy,
  showChannelNumber,
}: ChannelsBrowseSectionProps) {
  const [search, setSearch] = useState("")

  const visibleRows = useMemo(() => {
    if (isServer) return rows
    const ordered = sortByNumber ? sortChannelsByNumber(rows) : rows
    const trimmed = search.trim().toLowerCase()
    if (!trimmed) return ordered
    return ordered.filter((channel) =>
      channelSearchName(channel).toLowerCase().includes(trimmed),
    )
  }, [rows, isServer, sortByNumber, search])

  const pageStart = pagination.pageIndex * pagination.pageSize
  const pageRows = isServer
    ? visibleRows
    : visibleRows.slice(pageStart, pageStart + pagination.pageSize)
  const rowCount = isServer ? serverRowCount : visibleRows.length

  // TODO: Validate
  const changeSearch = (value: string) => {
    setSearch(value)
    onPaginationChange({ ...pagination, pageIndex: 0 })
  }

  return (
    <>
      {!isServer && (
        <div className="px-[4%] pb-4">
          <div className="relative max-w-sm">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(event) => changeSearch(event.target.value)}
              placeholder="Search channels"
              className="pl-8"
            />
          </div>
        </div>
      )}

      <ChannelsBrowse
        channels={pageRows}
        readOnly={readOnly}
        personalizable={personalizable}
        showCreatedBy={showCreatedBy}
        showChannelNumber={showChannelNumber}
      />

      <BrowsePagination
        pagination={pagination}
        onPaginationChange={onPaginationChange}
        rowCount={rowCount}
      />
    </>
  )
}
