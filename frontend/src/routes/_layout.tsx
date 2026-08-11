// TODO: Validate
import { createFileRoute, Outlet } from "@tanstack/react-router"

import { Footer } from "@/components/Common/Footer"
import { TopNav } from "@/components/TopNav/TopNav"
import { TooltipProvider } from "@/components/ui/tooltip"

export const Route = createFileRoute("/_layout")({
  component: Layout,
})

// TODO: Validate
function Layout() {
  return (
    <TooltipProvider>
      <div className="min-h-screen flex flex-col">
        <TopNav />
        <main className="flex-1 pt-16">
          <Outlet />
        </main>
        <Footer />
      </div>
    </TooltipProvider>
  )
}

export default Layout
