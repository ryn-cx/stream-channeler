import { createFileRoute, redirect } from "@tanstack/react-router"
import type { SortKeyInput } from "@/client"
import { OnboardingDone } from "@/components/Onboarding/Onboarding"
import { isLoggedIn } from "@/hooks/useAuth"

type DoneSearch = {
  sortBy?: SortKeyInput[]
}

export const Route = createFileRoute("/_layout/onboarding/$channelId/done")({
  component: RouteComponent,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  validateSearch: (search: Record<string, unknown>): DoneSearch => ({
    sortBy: search.sortBy as SortKeyInput[] | undefined,
  }),
  head: () => ({
    meta: [{ title: "All Set - Stream Channeler" }],
  }),
})

function RouteComponent() {
  const { channelId } = Route.useParams()
  const { sortBy } = Route.useSearch()
  return <OnboardingDone channelId={channelId} sortBy={sortBy} />
}
