// TODO: Validate
import { createFileRoute, redirect } from "@tanstack/react-router"

import { ChannelsService } from "@/client"
import { Dashboard } from "@/components/Dashboard/Dashboard"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/dashboard")({
  component: Dashboard,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
    try {
      const channels = await ChannelsService.getChannels({ scope: "owned" })
      if (channels.data.length === 0) {
        throw redirect({ to: "/onboarding" })
      }
    } catch (error) {
      if (error instanceof Response || (error as any)?.to === "/onboarding") {
        throw error
      }
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
