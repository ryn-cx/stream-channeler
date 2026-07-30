// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import type { ColumnDef } from "@tanstack/react-table"
import { Pencil, Trash2 } from "lucide-react"
import { useState } from "react"

import { type ChannelOrderListOutput, ChannelOrdersService } from "@/client"
import { FavoriteChannelOrder } from "@/components/ChannelOrders/FavoriteChannelOrder"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { Button } from "@/components/ui/button"
import { isLoggedIn } from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { orderSortStepCount } from "@/lib/channelOrder"
import { visibilityLabel } from "@/lib/visibility"
import { handleError } from "@/utils"

// One row shape now serves every scope and viewer.
export type OrderRow = ChannelOrderListOutput

export function OrderRowActions({
  order,
  isOwn,
  onEditConfig,
}: {
  order: OrderRow
  isOwn: boolean
  onEditConfig?: (order: OrderRow) => void
}) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [deleteOpen, setDeleteOpen] = useState(false)

  const deleteMutation = useMutation({
    mutationFn: () =>
      ChannelOrdersService.deleteChannelOrder({ channelOrderId: order.id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["channel-orders"] })
      showSuccessToast("Order deleted")
    },
    onError: handleError.bind(showErrorToast),
  })

  return (
    <div className="flex justify-end gap-1">
      {isLoggedIn() && <FavoriteChannelOrder orderId={order.id} />}
      {isOwn && onEditConfig && (
        <TooltipIconButton
          label="Edit"
          icon={<Pencil className="size-4" />}
          onClick={() => onEditConfig(order)}
        />
      )}
      {isOwn && (
        <TooltipIconButton
          label="Delete"
          icon={<Trash2 className="size-4 text-destructive" />}
          onClick={() => setDeleteOpen(true)}
        />
      )}

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete channel order?"
        description="This permanently deletes this saved order. Channels that reference it will fall back to their own sorting."
        confirmLabel="Delete"
        onConfirm={() => deleteMutation.mutate()}
      />
    </div>
  )
}

function ownerLabel(order: OrderRow): string {
  const username = "username" in order ? order.username : null
  return order.anonymous ? "Anonymous" : (username ?? "N/A")
}

function scoreColumn(): ColumnDef<OrderRow> {
  return {
    id: "score",
    accessorFn: (row) => ("score" in row ? row.score : null),
    header: "Score",
    enableColumnFilter: false,
    cell: ({ row }) => (
      <span className="tabular-nums">
        {"score" in row.original ? row.original.score : "—"}
      </span>
    ),
  }
}

function baseOrderColumns(
  includeOwner: boolean,
  includeScore = false,
): ColumnDef<OrderRow>[] {
  const cols: ColumnDef<OrderRow>[] = [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => (
        <span className="font-medium">
          {row.original.name ?? "Untitled order"}
        </span>
      ),
    },
    {
      accessorKey: "description",
      header: "Description",
      cell: ({ row }) => (
        <span className="line-clamp-2 text-muted-foreground">
          {row.original.description ?? "—"}
        </span>
      ),
    },
  ]

  if (includeOwner) {
    cols.push({
      accessorFn: (row) => ("username" in row ? row.username : null),
      id: "username",
      header: "Owner",
      cell: ({ row }) => (
        <span className="text-muted-foreground">
          {ownerLabel(row.original)}
        </span>
      ),
    })
  }

  cols.push(
    {
      accessorFn: (row) => visibilityLabel(row.visibility),
      id: "visibility",
      header: "Visibility",
    },
    {
      id: "steps",
      header: "Sort Steps",
      enableColumnFilter: false,
      cell: ({ row }) => (
        <span className="tabular-nums">
          {orderSortStepCount(row.original.config)}
        </span>
      ),
    },
  )

  if (includeScore) {
    cols.push(scoreColumn())
  }

  return cols
}

export function orderColumns({
  isOwn,
  isAdmin = false,
  onEditConfig,
}: {
  isOwn: boolean
  isAdmin?: boolean
  onEditConfig?: (order: OrderRow) => void
}): ColumnDef<OrderRow>[] {
  // Admins can edit or delete any order, so the row actions follow the viewer's
  // permissions rather than the tab the table is rendered on.
  const canManage = isOwn || isAdmin
  const cols = baseOrderColumns(!isOwn, isAdmin)
  cols.push({
    id: "actions",
    header: "",
    enableColumnFilter: false,
    cell: ({ row }) => (
      <OrderRowActions
        order={row.original}
        isOwn={canManage}
        onEditConfig={onEditConfig}
      />
    ),
  })

  return cols
}

export function publicOrderPickerColumns(
  onUse: (order: ChannelOrderListOutput) => void,
): ColumnDef<OrderRow>[] {
  const cols = baseOrderColumns(true)
  cols.push({
    id: "actions",
    header: "",
    enableColumnFilter: false,
    cell: ({ row }) => (
      <div className="flex justify-end">
        <Button
          size="sm"
          onClick={() => onUse(row.original as ChannelOrderListOutput)}
        >
          Use
        </Button>
      </div>
    ),
  })

  return cols
}
