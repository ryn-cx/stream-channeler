// TODO: Validate
import { Outlet, createFileRoute, redirect } from "@tanstack/react-router"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/onboarding")({
  component: Outlet,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [
      {
        title: "Get Started - Stream Channeler",
      },
    ],
  }),
})
