// TODO: Validate
import { Link, useRouterState } from "@tanstack/react-router"
import {
  Eye,
  LayoutDashboard,
  Library,
  ListOrdered,
  LogIn,
  LogOut,
  Menu,
  MessageSquare,
  Plug,
  Radio,
  Settings,
  Users,
} from "lucide-react"
import { useEffect, useState } from "react"

import { Appearance } from "@/components/Common/Appearance"
import { Logo } from "@/components/Common/Logo"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import { cn } from "@/lib/utils"
import { getInitials } from "@/utils"

interface NavItem {
  icon: React.ElementType
  title: string
  path: string
}

const baseItems: NavItem[] = [
  { icon: LayoutDashboard, title: "Dashboard", path: "/dashboard" },
  { icon: Radio, title: "Channels", path: "/channels" },
  { icon: Eye, title: "Watches", path: "/watches" },
  { icon: MessageSquare, title: "Comments", path: "/channel-comments" },
  { icon: ListOrdered, title: "Orders", path: "/channel-orders" },
  { icon: Plug, title: "Custom Media", path: "/plugins" },
]

const adminItems: NavItem[] = [
  ...baseItems,
  { icon: Library, title: "Canonical Media", path: "/admin/canonical-shows" },
  { icon: Users, title: "Admin", path: "/admin" },
]

const publicItems: NavItem[] = [
  { icon: Radio, title: "Channels", path: "/channels" },
]

// TODO: Validate
function NavLinks({
  items,
  onClick,
}: {
  items: NavItem[]
  onClick?: () => void
}) {
  const router = useRouterState()
  const currentPath = router.location.pathname

  return (
    <>
      {items.map((item) => {
        const isActive = currentPath === item.path
        return (
          <Link
            key={item.path}
            to={item.path}
            onClick={onClick}
            className={cn(
              "text-sm transition-colors hover:text-foreground",
              isActive
                ? "text-foreground font-bold"
                : "text-muted-foreground font-medium",
            )}
          >
            {item.title}
          </Link>
        )
      })}
    </>
  )
}

// TODO: Validate
function MobileNavLinks({
  items,
  onClick,
}: {
  items: NavItem[]
  onClick?: () => void
}) {
  const router = useRouterState()
  const currentPath = router.location.pathname

  return (
    <div className="flex flex-col gap-1 mt-4">
      {items.map((item) => {
        const isActive = currentPath === item.path
        const Icon = item.icon
        return (
          <Link
            key={item.path}
            to={item.path}
            onClick={onClick}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
            )}
          >
            <Icon className="size-4" />
            {item.title}
          </Link>
        )
      })}
    </div>
  )
}

// TODO: Validate
function UserMenu() {
  const { user: currentUser, logout } = useAuth()

  if (!currentUser) return null

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="rounded-full"
          data-testid="user-menu"
        >
          <Avatar className="size-8">
            <AvatarFallback className="bg-zinc-600 text-white text-xs">
              {getInitials(currentUser.username)}
            </AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col">
            <p className="text-sm font-medium">{currentUser.username}</p>
            <p className="text-xs text-muted-foreground">{currentUser.email}</p>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <Link to="/settings">
          <DropdownMenuItem>
            <Settings className="size-4" />
            Settings
          </DropdownMenuItem>
        </Link>
        <DropdownMenuItem onClick={() => logout()}>
          <LogOut className="size-4" />
          Log Out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

// TODO: Validate
export function TopNav() {
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const { user: currentUser } = useAuth()
  const loggedIn = isLoggedIn()

  const items = loggedIn
    ? currentUser?.is_superuser
      ? adminItems
      : baseItems
    : publicItems

  useEffect(() => {
    // TODO: Validate
    const handleScroll = () => setScrolled(window.scrollY > 10)
    window.addEventListener("scroll", handleScroll, { passive: true })
    return () => window.removeEventListener("scroll", handleScroll)
  }, [])

  return (
    <header
      className={cn(
        // Below the z-50 overlay primitives (dialog/sheet/dropdown/popover) so
        // menus opened near the top of the page are not painted over.
        "fixed top-0 left-0 right-0 z-40 transition-colors duration-300",
        scrolled
          ? "bg-background/95 backdrop-blur-md border-b border-border/50"
          : "bg-gradient-to-b from-background/80 to-transparent",
      )}
    >
      <div className="flex h-16 items-center gap-6 px-4 md:px-8">
        {/* Mobile menu */}
        <div className="md:hidden">
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon">
                <Menu className="size-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-72">
              <SheetHeader>
                <SheetTitle>
                  <Logo variant="full" className="h-8" />
                </SheetTitle>
              </SheetHeader>
              <MobileNavLinks
                items={items}
                onClick={() => setMobileOpen(false)}
              />
              {!loggedIn && (
                <div className="mt-1 flex flex-col gap-1">
                  <Link
                    to="/login"
                    onClick={() => setMobileOpen(false)}
                    className="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                  >
                    <LogIn className="size-4" />
                    Log In
                  </Link>
                </div>
              )}
            </SheetContent>
          </Sheet>
        </div>

        {/* Logo */}
        <Logo variant="full" className="h-9" />

        {/* Desktop nav links */}
        <nav className="hidden md:flex items-center gap-6">
          <NavLinks items={items} />
        </nav>

        {/* Right side */}
        <div className="ml-auto flex items-center gap-2">
          <Appearance />
          {loggedIn ? (
            <UserMenu />
          ) : (
            <Button variant="default" size="sm" asChild>
              <Link to="/login">Sign In</Link>
            </Button>
          )}
        </div>
      </div>
    </header>
  )
}
