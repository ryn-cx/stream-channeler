// TODO: Validate
import type { ReactNode } from "react"

// Title + scope switcher on the left, page actions on the right, matching the
// orders page header.
export function ChannelsHeader({
  scopeTabs,
  children,
}: {
  scopeTabs: ReactNode
  children?: ReactNode
}) {
  return (
    <div className="flex items-center justify-between gap-2 px-[4%] pt-4 pb-2">
      <div className="flex min-w-0 items-center gap-3">
        <h1 className="text-2xl font-bold tracking-tight">Channels</h1>
        {scopeTabs}
      </div>
      {children ? (
        <div className="flex shrink-0 items-center gap-2">{children}</div>
      ) : null}
    </div>
  )
}
