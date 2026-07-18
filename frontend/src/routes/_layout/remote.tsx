// TODO: Validate
import { createFileRoute } from "@tanstack/react-router"

import { RemotePage } from "@/components/Remote/RemotePage"

export const Route = createFileRoute("/_layout/remote")({
  component: RemotePage,
  head: () => ({
    meta: [
      {
        title: "Stream Channeler Remote - Stream Channeler",
      },
    ],
  }),
})
