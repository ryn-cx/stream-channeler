import { createFileRoute, redirect } from "@tanstack/react-router"
import { OnboardingDone } from "@/components/Onboarding/Onboarding"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/onboarding/$channelId/done")({
  component: RouteComponent,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "All Set - Stream Channeler" }],
  }),
})

function RouteComponent() {
  const { channelId } = Route.useParams()
  return <OnboardingDone channelId={channelId} />
}
