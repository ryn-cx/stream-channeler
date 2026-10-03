// TODO: Validate
import { createFileRoute, redirect } from "@tanstack/react-router"
import { OnboardingEditName } from "@/components/Onboarding/Onboarding"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/onboarding/$channelId/name")({
  component: RouteComponent,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Edit Channel Name - Stream Channeler" }],
  }),
})

// TODO: Validate
function RouteComponent() {
  const { channelId } = Route.useParams()
  return <OnboardingEditName channelId={channelId} />
}
