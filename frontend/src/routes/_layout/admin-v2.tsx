// TODO: Validate
import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"
import { UsersService } from "@/client"

export const Route = createFileRoute("/_layout/admin-v2")({
  component: AdminV2Layout,
  beforeLoad: async () => {
    const user = await UsersService.readUserMe()
    if (!user.is_superuser) {
      throw redirect({
        to: "/",
      })
    }
  },
})

// TODO: Validate
function AdminV2Layout() {
  return <Outlet />
}
