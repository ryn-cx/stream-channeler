import { createFileRoute } from "@tanstack/react-router"

import { InfoPage } from "@/components/Home/InfoPage"

export const Route = createFileRoute("/_layout/")({
  component: InfoPage,
  head: () => ({
    meta: [
      {
        title: "Stream Channeler",
      },
    ],
  }),
})
