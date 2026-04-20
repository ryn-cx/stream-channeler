import { createFileRoute, redirect } from "@tanstack/react-router"
import { OnboardingSort } from "@/components/Onboarding/Onboarding"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/onboarding/$channelId/sort")({
  component: RouteComponent,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Choose Sort - Stream Channeler" }],
  }),
})

function RouteComponent() {
  const { channelId } = Route.useParams()
  return <OnboardingSort channelId={channelId} />
}
