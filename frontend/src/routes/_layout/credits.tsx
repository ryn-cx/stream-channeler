// TODO: Validate
import { createFileRoute } from "@tanstack/react-router"

export const Route = createFileRoute("/_layout/credits")({
  component: Credits,
  head: () => ({
    meta: [{ title: "Credits - Stream Channeler" }],
  }),
})

function Credits() {
  return (
    <div className="container mx-auto max-w-3xl px-4 py-16">
      <h1 className="text-4xl font-bold tracking-tight">Credits</h1>

      <section className="mt-8 rounded-lg border p-6">
        <img
          src="/tmdb.svg"
          alt="The Movie Database (TMDB)"
          className="h-5 w-auto"
        />
        <p className="mt-4 max-w-xl text-sm text-muted-foreground">
          This product uses the TMDB API but is not endorsed or certified by
          TMDB.
        </p>
      </section>
    </div>
  )
}
