// TODO: Validate
import { keepPreviousData, useQuery } from "@tanstack/react-query"
import type {
  ColumnFiltersState,
  PaginationState,
  SortingState,
} from "@tanstack/react-table"
import { useState } from "react"

import { type ChannelOrderListOutput, ChannelOrdersService } from "@/client"
import { publicOrderPickerColumns } from "@/components/ChannelOrders/orderColumns"
import { DataTable, serializeTableQuery } from "@/components/Common/DataTable"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

// TODO: Validate
export function PublicOrderPickerDialog({
  onUse,
  disabled = false,
}: {
  onUse: (order: ChannelOrderListOutput) => void
  disabled?: boolean
}) {
  const [open, setOpen] = useState(false)
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  })
  const [sortOptions, setSortOptions] = useState<SortingState>([])
  const [filterOptions, setFilterOptions] = useState<ColumnFiltersState>([])

  const ordersQuery = useQuery({
    queryKey: [
      "channel-orders",
      "public",
      "picker",
      pagination,
      sortOptions,
      filterOptions,
    ],
    queryFn: () =>
      ChannelOrdersService.getChannelOrders({
        scope: "public",
        offset: pagination.pageIndex * pagination.pageSize,
        limit: pagination.pageSize,
        ...serializeTableQuery(
          {
            offset: pagination.pageIndex * pagination.pageSize,
            limit: pagination.pageSize,
            sortOptions,
            filterOptions,
          },
          publicOrderPickerColumns(() => {}),
        ),
      }),
    enabled: open,
    placeholderData: keepPreviousData,
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button type="button" variant="outline" disabled={disabled}>
          Search public orders
        </Button>
      </DialogTrigger>
      {/* Wider than the filters dialog it opens from, so the orders table fits. */}
      <DialogContent className="sm:max-w-5xl lg:max-w-6xl max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Search public orders</DialogTitle>
          <DialogDescription>
            Pick a public order to load into this channel's options.
          </DialogDescription>
        </DialogHeader>
        <div className="flex-1 min-h-0 overflow-y-auto">
          {ordersQuery.data === undefined ? (
            <p className="text-sm text-muted-foreground">
              Loading public orders...
            </p>
          ) : (
            <div
              className={
                ordersQuery.isPlaceholderData
                  ? "overflow-x-auto opacity-60 transition-opacity duration-200"
                  : "overflow-x-auto"
              }
            >
              <DataTable
                columns={publicOrderPickerColumns((order) => {
                  setOpen(false)
                  onUse(order)
                })}
                data={ordersQuery.data.data}
                serverSide={{
                  pagination,
                  sortOptions,
                  filterOptions,
                  onPaginationChange: setPagination,
                  onSortOptionsChange: setSortOptions,
                  onFilterOptionsChange: setFilterOptions,
                  rowCount: ordersQuery.data.filtered_count,
                  totalRowCount: ordersQuery.data.total_count,
                }}
              />
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
