// TODO: Validate
import {
  type OrderRow,
  OrderRowActions,
} from "@/components/ChannelOrders/orderColumns"

// The card style is the one the onboarding sort step uses to present orders:
// an emoji icon, the name, and the description on a bordered row.
// TODO: Validate
export function OrdersBrowse({
  orders,
  canManage,
  onEditConfig,
}: {
  orders: OrderRow[]
  canManage: boolean
  onEditConfig?: (order: OrderRow) => void
}) {
  return (
    <div className="grid gap-3 px-[4%] pb-8">
      {orders.map((order) => (
        <div
          key={order.id}
          className="flex items-center gap-4 rounded-lg border border-border p-4 text-left transition-colors hover:bg-accent/50"
        >
          {order.icon && (
            <div className="shrink-0 text-4xl leading-none">{order.icon}</div>
          )}
          <div className="min-w-0 flex-1">
            <p className="font-medium">{order.name || "Untitled order"}</p>
            {order.description && (
              <p className="text-sm text-muted-foreground">
                {order.description}
              </p>
            )}
          </div>
          <OrderRowActions
            order={order}
            isOwn={canManage}
            onEditConfig={onEditConfig}
          />
        </div>
      ))}
    </div>
  )
}
