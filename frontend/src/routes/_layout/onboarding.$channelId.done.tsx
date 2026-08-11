// TODO: Validate
import { createFileRoute, redirect } from "@tanstack/react-router"
import { OnboardingDone } from "@/components/Onboarding/Onboarding"
import { isLoggedIn } from "@/hooks/useAuth"

type DoneSearch = {
  orderPresetId?: string
}

export const Route = createFileRoute("/_layout/onboarding/$channelId/done")({
  component: RouteComponent,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  validateSearch: (search: Record<string, unknown>): DoneSearch => ({
    orderPresetId: search.orderPresetId as string | undefined,
  }),
  head: () => ({
    meta: [{ title: "All Set - Stream Channeler" }],
  }),
})

// TODO: Validate
function RouteComponent() {
  const { channelId } = Route.useParams()
  const { orderPresetId } = Route.useSearch()
  return <OnboardingDone channelId={channelId} orderPresetId={orderPresetId} />
}
