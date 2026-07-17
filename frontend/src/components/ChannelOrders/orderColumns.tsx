// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import type { ColumnDef } from "@tanstack/react-table"
import { Copy, Pencil, Trash2 } from "lucide-react"
import { useState } from "react"

import {
  type ChannelOrderAdminOutput,
  type ChannelOrderOutput,
  type ChannelOrderPublicOutput,
  ChannelOrdersService,
} from "@/client"
import { CopyChannelOrderDialog } from "@/components/ChannelOrders/CopyChannelOrderDialog"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { orderSortStepCount } from "@/lib/channelOrder"
import { visibilityLabel } from "@/lib/visibility"
import { handleError } from "@/utils"

export type OrderRow =
  | ChannelOrderOutput
  | ChannelOrderPublicOutput
  | ChannelOrderAdminOutput

function OrderRowActions({
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
  const [copyOpen, setCopyOpen] = useState(false)
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
      <TooltipIconButton
        label="Copy to your account"
        icon={<Copy className="size-4" />}
        onClick={() => setCopyOpen(true)}
      />
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

      {copyOpen && (
        <CopyChannelOrderDialog
          order={order}
          open={copyOpen}
          onOpenChange={setCopyOpen}
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
  return order.anonymous ? "Anonymous" : username?.trim() || "N/A"
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
  onUse: (order: ChannelOrderPublicOutput) => void,
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
          onClick={() => onUse(row.original as ChannelOrderPublicOutput)}
        >
          Use
        </Button>
      </div>
    ),
  })

  return cols
}
