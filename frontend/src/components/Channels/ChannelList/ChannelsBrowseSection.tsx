// TODO: Validate
import type { PaginationState } from "@tanstack/react-table"
import { useMemo } from "react"

import type { ChannelListOutput } from "@/client"
import { ChannelSearchInput } from "@/components/Channels/ChannelList/ChannelSearchInput"
import {
  type BrowseChannel,
  ChannelsBrowse,
  sortChannelsByNumber,
} from "@/components/Channels/ChannelList/ChannelsBrowse"
import { usePrefetchNeighborPageEpisodes } from "@/components/Channels/ChannelList/useChannelEpisodePreview"
import { BrowsePagination } from "@/components/Common/BrowsePagination"

// Favorites have the viewer's private name, which is what they see and search on.
// TODO: Validate
export function channelSearchName(channel: BrowseChannel): string {
  return (channel as ChannelListOutput).custom_name ?? channel.name ?? ""
}

interface ChannelsBrowseSectionProps {
  rows: BrowseChannel[]
  search: string
  onSearchChange: (search: string) => void
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

// TODO: Validate
export function ChannelsBrowseSection({
  rows,
  search,
  onSearchChange,
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
  const visibleRows = useMemo(() => {
    if (isServer) return rows
    const ordered = sortByNumber ? sortChannelsByNumber(rows) : rows
    const trimmed = search.trim().toLowerCase()
    if (!trimmed) return ordered
    return ordered.filter((channel) =>
      channelSearchName(channel).toLowerCase().includes(trimmed),
    )
  }, [rows, isServer, sortByNumber, search])

  usePrefetchNeighborPageEpisodes(visibleRows, pagination, !isServer)

  const pageStart = pagination.pageIndex * pagination.pageSize
  const pageRows = isServer
    ? visibleRows
    : visibleRows.slice(pageStart, pageStart + pagination.pageSize)
  const rowCount = isServer ? serverRowCount : visibleRows.length

  // TODO: Validate
  const changeSearch = (value: string) => {
    onSearchChange(value)
    onPaginationChange({ ...pagination, pageIndex: 0 })
  }

  return (
    <>
      <div className="px-[4%] pb-4">
        <ChannelSearchInput value={search} onValueChange={changeSearch} />
      </div>

      <ChannelsBrowse
        channels={pageRows}
        readOnly={readOnly}
        personalizable={personalizable}
        showCreatedBy={showCreatedBy}
        showChannelNumber={showChannelNumber}
      />

      <div className="sticky bottom-0 z-30 border-t border-border/50 bg-background/95 pt-2 backdrop-blur-md [&>div:last-child]:pb-3">
        <BrowsePagination
          pagination={pagination}
          onPaginationChange={onPaginationChange}
          rowCount={rowCount}
        />
      </div>
    </>
  )
}
