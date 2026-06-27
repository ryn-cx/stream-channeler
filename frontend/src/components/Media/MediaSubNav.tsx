// TODO: Validate
import { Link, useRouterState } from "@tanstack/react-router"

import { cn } from "@/lib/utils"

const items = [
  { title: "Plugins", path: "/plugins" },
  { title: "Sources", path: "/sources" },
  { title: "Shows", path: "/shows" },
  { title: "Seasons", path: "/seasons" },
  { title: "Episodes", path: "/episodes" },
] as const

// Secondary navigation shown on every custom-media page so the user can jump
// between the different media types they own.
export function MediaSubNav() {
  const router = useRouterState()
  const currentPath = router.location.pathname

  return (
    <nav className="flex flex-wrap items-center gap-4 border-b px-[4%] py-2">
      {items.map((item) => {
        const isActive = currentPath === item.path
        return (
          <Link
            key={item.path}
            to={item.path}
            className={cn(
              "text-sm transition-colors hover:text-foreground",
              isActive
                ? "font-semibold text-foreground"
                : "text-muted-foreground",
            )}
          >
            {item.title}
          </Link>
        )
      })}
    </nav>
  )
}
