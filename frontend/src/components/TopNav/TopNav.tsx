// TODO: Validate
import { Link, useRouterState } from "@tanstack/react-router"
import {
  Eye,
  Globe,
  LayoutDashboard,
  ListMusic,
  LogIn,
  LogOut,
  Menu,
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
  { icon: Radio, title: "My Channels", path: "/channels" },
  { icon: Globe, title: "Public Channels", path: "/channels/browse" },
  { icon: ListMusic, title: "Playlists", path: "/playlists" },
  { icon: Eye, title: "Watches", path: "/watches" },
  { icon: Plug, title: "Custom Media", path: "/plugins" },
]

const adminItems: NavItem[] = [
  ...baseItems,
  { icon: Users, title: "Admin", path: "/admin" },
]

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
              "text-sm transition-colors hover:text-white",
              isActive
                ? "text-white font-bold"
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
              {getInitials(currentUser.username || "User")}
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

export function TopNav() {
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const { user: currentUser } = useAuth()
  const loggedIn = isLoggedIn()

  const items = currentUser?.is_superuser ? adminItems : baseItems

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 10)
    window.addEventListener("scroll", handleScroll, { passive: true })
    return () => window.removeEventListener("scroll", handleScroll)
  }, [])

  return (
    <header
      className={cn(
        "fixed top-0 left-0 right-0 z-50 transition-colors duration-300",
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
              {loggedIn ? (
                <MobileNavLinks
                  items={items}
                  onClick={() => setMobileOpen(false)}
                />
              ) : (
                <div className="mt-4">
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
        {loggedIn && (
          <nav className="hidden md:flex items-center gap-6">
            <NavLinks items={items} />
          </nav>
        )}

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
