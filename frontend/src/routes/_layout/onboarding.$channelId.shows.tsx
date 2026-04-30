// TODO: Validate
import { createFileRoute, redirect } from "@tanstack/react-router"
import { OnboardingShows } from "@/components/Onboarding/Onboarding"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/onboarding/$channelId/shows")({
  component: RouteComponent,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Add Shows - Stream Channeler" }],
  }),
})

function RouteComponent() {
  const { channelId } = Route.useParams()
  return <OnboardingShows channelId={channelId} />
}
