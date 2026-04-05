// TODO: Validate
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Onboarding } from "@/components/Onboarding/Onboarding"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/onboarding")({
  component: Onboarding,
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
