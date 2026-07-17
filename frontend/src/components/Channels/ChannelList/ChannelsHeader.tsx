// TODO: Validate
import type { ReactNode } from "react"

// Title + scope switcher + view switcher on the left, page actions on the right,
// matching the orders page header.
export function ChannelsHeader({
  scopeTabs,
  viewTabs,
  children,
}: {
  scopeTabs: ReactNode
  viewTabs?: ReactNode
  children?: ReactNode
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 px-[4%] pt-4 pb-2">
      <div className="flex min-w-0 flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold tracking-tight">Channels</h1>
        {scopeTabs}
        {viewTabs}
      </div>
      {children ? (
        <div className="flex shrink-0 items-center gap-2">{children}</div>
      ) : null}
    </div>
  )
}
