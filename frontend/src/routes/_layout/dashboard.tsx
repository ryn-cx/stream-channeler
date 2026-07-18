// TODO: Validate
import { createFileRoute, redirect } from "@tanstack/react-router"

import { Dashboard } from "@/components/Dashboard/Dashboard"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/dashboard")({
  component: Dashboard,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [
      {
        title: "Dashboard - Stream Channeler",
      },
    ],
  }),
})
