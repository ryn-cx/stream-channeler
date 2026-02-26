// TODO: Validate
import { createFileRoute, Outlet } from "@tanstack/react-router"

import { Footer } from "@/components/Common/Footer"
import AppSidebar from "@/components/Sidebar/AppSidebar"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar"
import { useIsMobile } from "@/hooks/useMobile"

export const Route = createFileRoute("/_layout")({
  component: Layout,
})

function LayoutContent() {
  const isMobile = useIsMobile()
  const { openMobile } = useSidebar()

  return (
    <SidebarInset>
      <div className="min-h-screen flex flex-col">
        <main className="flex-1 p-4 md:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
      <Footer />
      {isMobile && !openMobile && (
        <footer className="sticky bottom-0 z-10 flex shrink-0 items-center gap-2 px-8 pb-4">
          <SidebarTrigger className="-ml-1 text-muted-foreground scale-[2]" />
        </footer>
      )}
    </SidebarInset>
  )
}

function Layout() {
  return (
    <SidebarProvider>
      <AppSidebar />
      <LayoutContent />
    </SidebarProvider>
  )
}

export default Layout
