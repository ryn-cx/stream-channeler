// TODO: Validate
import { Link, useRouterState } from "@tanstack/react-router"

import { validateMediaSearch } from "@/components/Common/DataTable"
import useAuth from "@/hooks/useAuth"
import { cn } from "@/lib/utils"

const baseItems = [
  { title: "Plugins", path: "/plugins" },
  { title: "Sources", path: "/sources" },
  { title: "Shows", path: "/shows" },
  { title: "Seasons", path: "/seasons" },
  { title: "Episodes", path: "/episodes" },
] as const

// Files are superuser-only, so this item is only shown to admins.
const adminItem = { title: "Files", path: "/files" } as const

// Secondary navigation shown on every custom-media page so the user can jump
// between the different media types they own.
// TODO: Validate
export function MediaSubNav() {
  const router = useRouterState()
  const currentPath = router.location.pathname
  const { user } = useAuth()
  const items = user?.is_superuser ? [...baseItems, adminItem] : baseItems

  const currentSearch = validateMediaSearch(
    router.location.search as Record<string, unknown>,
  )

  return (
    <nav className="flex flex-wrap items-center gap-4 border-b px-[4%] py-2">
      {items.map((item) => {
        const isActive = currentPath === item.path
        return (
          <Link
            key={item.path}
            to={item.path}
            search={currentSearch}
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
