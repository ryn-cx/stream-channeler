// TODO: Validate
import { createFileRoute, redirect } from "@tanstack/react-router"
import { OnboardingTitles } from "@/components/Onboarding/Onboarding"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/onboarding/$channelId/titles")({
  component: RouteComponent,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Add Titles - Stream Channeler" }],
  }),
})

// TODO: Validate
function RouteComponent() {
  const { channelId } = Route.useParams()
  return <OnboardingTitles channelId={channelId} />
}
