import { Link, type LinkProps } from "@tanstack/react-router"
import { MoreVertical } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetTrigger,
} from "@/components/ui/sheet"
import { useIsTouchDevice } from "@/hooks/useMobile"
import { cn } from "@/lib/utils"

export type ActionMenuItem = {
  key: string
  icon: React.ReactNode
  label: React.ReactNode
  onClick?: (event: React.MouseEvent) => void
  disabled?: boolean
  /** Render the item as a TanStack Router link instead of a button. */
  to?: LinkProps["to"]
  params?: LinkProps["params"]
}

interface ResponsiveActionMenuProps {
  items: ActionMenuItem[]
  /** Trigger button rendered to open the menu. Defaults to a ghost MoreVertical icon. */
  trigger?: React.ReactNode
  /** Desktop dropdown alignment. */
  align?: "start" | "center" | "end"
  /** Forwarded to the trigger so the card click doesn't fire underneath. */
  onTriggerClick?: (event: React.MouseEvent) => void
}

function MenuRow({
  item,
  className,
}: {
  item: ActionMenuItem
  className?: string
}) {
  const baseClass = cn(
    "flex w-full items-center gap-3 rounded-md px-3 py-3 text-left text-base outline-hidden",
    "hover:bg-accent focus:bg-accent disabled:pointer-events-none disabled:opacity-50",
    "[&_svg]:size-5 [&_svg]:shrink-0",
    className,
  )
  if (item.to) {
    return (
      <Link
        to={item.to}
        params={item.params}
        className={baseClass}
        onClick={item.onClick}
      >
        {item.icon}
        <span className="flex-1">{item.label}</span>
      </Link>
    )
  }
  return (
    <button
      type="button"
      className={baseClass}
      onClick={item.onClick}
      disabled={item.disabled}
    >
      {item.icon}
      <span className="flex-1">{item.label}</span>
    </button>
  )
}

export function ResponsiveActionMenu({
  items,
  trigger,
  align = "end",
  onTriggerClick,
}: ResponsiveActionMenuProps) {
  const isTouch = useIsTouchDevice()

  const defaultTrigger = (
    <Button
      variant="ghost"
      size="icon"
      className="h-8 w-8 bg-background/80 hover:bg-background/90 backdrop-blur-sm"
      onClick={onTriggerClick}
    >
      <MoreVertical className="h-4 w-4" />
      <span className="sr-only">Open menu</span>
    </Button>
  )

  const triggerNode = trigger ?? defaultTrigger

  if (isTouch) {
    return (
      <Sheet>
        <SheetTrigger asChild>{triggerNode}</SheetTrigger>
        <SheetContent
          side="bottom"
          className="rounded-t-xl pt-3 pb-[env(safe-area-inset-bottom)]"
          onClick={(event) => event.stopPropagation()}
        >
          <div
            aria-hidden
            className="mx-auto mb-2 h-1.5 w-10 rounded-full bg-muted"
          />
          <div className="flex flex-col gap-1 px-2 pb-4">
            {items.map((item) => (
              <SheetClose key={item.key} asChild>
                <MenuRow item={item} />
              </SheetClose>
            ))}
          </div>
        </SheetContent>
      </Sheet>
    )
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>{triggerNode}</DropdownMenuTrigger>
      <DropdownMenuContent
        align={align}
        onClick={(event) => event.stopPropagation()}
      >
        {items.map((item) =>
          item.to ? (
            <DropdownMenuItem key={item.key} asChild disabled={item.disabled}>
              <Link to={item.to} params={item.params} onClick={item.onClick}>
                {item.icon}
                {item.label}
              </Link>
            </DropdownMenuItem>
          ) : (
            <DropdownMenuItem
              key={item.key}
              onClick={item.onClick}
              disabled={item.disabled}
            >
              {item.icon}
              {item.label}
            </DropdownMenuItem>
          ),
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
