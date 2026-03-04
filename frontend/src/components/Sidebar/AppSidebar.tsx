// TODO: Validate
import { Link } from "@tanstack/react-router"
import {
  Eye,
  Home,
  LayoutDashboard,
  LogIn,
  PanelLeftClose,
  Plug,
  Radio,
  Users,
} from "lucide-react"

import { SidebarAppearance } from "@/components/Common/Appearance"
import { Logo } from "@/components/Common/Logo"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import { type Item, Main } from "./Main"
import { User } from "./User"

const baseItems: Item[] = [
  { icon: Home, title: "Home", path: "/" },
  { icon: LayoutDashboard, title: "Dashboard", path: "/dashboard" },
  { icon: Radio, title: "Channels", path: "/channels" },
  { icon: Eye, title: "Watches", path: "/watches" },
  { icon: Plug, title: "Custom Media", path: "/plugin" },
]

const unauthenticatedItems: Item[] = [{ icon: Home, title: "Home", path: "/" }]

const adminItems: Item[] = [
  ...baseItems,
  { icon: Users, title: "Admin", path: "/admin" },
]

export function AppSidebar() {
  const { user: currentUser } = useAuth()
  const { toggleSidebar } = useSidebar()
  const loggedIn = isLoggedIn()

  const items = !loggedIn
    ? unauthenticatedItems
    : currentUser?.is_superuser
      ? adminItems
      : baseItems

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="px-4 py-6 group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:items-center">
        <Logo variant="responsive" />
      </SidebarHeader>
      <SidebarContent>
        <Main items={items} />
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  tooltip="Toggle Sidebar"
                  onClick={toggleSidebar}
                >
                  <PanelLeftClose />
                  <span>Toggle Sidebar</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <SidebarAppearance />
        {loggedIn ? (
          <User user={currentUser} />
        ) : (
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton asChild tooltip="Log In">
                <Link to="/login">
                  <LogIn />
                  <span>Log In</span>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        )}
      </SidebarFooter>
    </Sidebar>
  )
}

export default AppSidebar
