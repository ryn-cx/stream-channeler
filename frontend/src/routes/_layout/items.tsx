import { useMutationState } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Search } from "lucide-react"

import type { ItemCreate } from "@/client"
import { ItemsService } from "@/client"
import { ServerClientTable } from "@/components/Common/DataTable"
import { PageHeader } from "@/components/Common/PageHeader"
import AddItem from "@/components/Items/AddItem"
import { columns } from "@/components/Items/columns"
import type { ItemPublicWithPending } from "@/components/Items/types"
import PendingItems from "@/components/Pending/PendingItems"

export const Route = createFileRoute("/_layout/items")({
  component: Items,
  head: () => ({
    meta: [
      {
        title: "Items - FastAPI Template",
      },
    ],
  }),
})

function ItemsTable() {
  const pendingItems = useMutationState({
    filters: { mutationKey: ["items", "create"], status: "pending" },
    select: (mutation): ItemPublicWithPending => ({
      ...(mutation.state.variables as ItemCreate),
      id: `pending-${mutation.mutationId}`,
      owner_id: "",
      pending: true,
    }),
  })

  return (
    <ServerClientTable<ItemPublicWithPending>
      columns={columns}
      queryKey={["items"]}
      fetchTable={({ offset, limit, sortOptions, filterOptions }) =>
        ItemsService.readItems({
          offset,
          limit,
          sortOptions: JSON.stringify(sortOptions),
          filterOptions: JSON.stringify(filterOptions),
        })
      }
      storageKey="items-table"
      pendingRows={pendingItems}
      rowClassName={(row) => (row.pending ? "opacity-50" : undefined)}
      loadingFallback={<PendingItems />}
      emptyState={
        <div className="flex flex-col items-center justify-center text-center py-12">
          <div className="rounded-full bg-muted p-4 mb-4">
            <Search className="h-8 w-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold">
            You don't have any items yet
          </h3>
          <p className="text-muted-foreground">Add a new item to get started</p>
        </div>
      }
    />
  )
}

function Items() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Items" description="Create and manage your items">
        <AddItem />
      </PageHeader>
      <ItemsTable />
    </div>
  )
}
