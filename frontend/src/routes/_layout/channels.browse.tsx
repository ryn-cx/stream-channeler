// TODO: Validate
import { createFileRoute, redirect } from "@tanstack/react-router"

export const Route = createFileRoute("/_layout/channels/browse")({
  beforeLoad: () => {
    throw redirect({ to: "/channels", search: { view: "public" } })
  },
})
