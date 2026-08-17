// TODO: Validate
import { createFileRoute } from "@tanstack/react-router"
import type { ReactNode } from "react"

export const Route = createFileRoute("/_layout/credits")({
  component: Credits,
  head: () => ({
    meta: [{ title: "Credits - Stream Channeler" }],
  }),
})

// TODO: Validate
function Credits() {
  return (
    <div className="container mx-auto max-w-3xl px-4 py-16">
      <h1 className="text-4xl font-bold tracking-tight">Credits</h1>

      <p className="mt-4 max-w-xl text-sm text-muted-foreground">
        Media information from TMDB, JustWatch, Watchmode, and the Stream
        Channeler Community.
      </p>

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
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          Titles, seasons, episodes, artwork, and the numbering everything is
          read in come from{" "}
          <CreditLink href="https://www.themoviedb.org">TMDB</CreditLink>.
        </p>
      </section>

      <section className="mt-4 rounded-lg border p-6">
        <h2 className="text-lg font-semibold">JustWatch</h2>
        <p className="mt-4 max-w-xl text-sm text-muted-foreground">
          Streaming availability - which services carry a title and where it can
          be watched - is provided by{" "}
          <CreditLink href="https://www.justwatch.com">JustWatch</CreditLink>.
          This product is not endorsed or certified by JustWatch.
        </p>
      </section>

      <section className="mt-4 rounded-lg border p-6">
        <h2 className="text-lg font-semibold">Watchmode</h2>
        <p className="mt-4 max-w-xl text-sm text-muted-foreground">
          Streaming availability is also provided by{" "}
          <CreditLink href="https://www.watchmode.com">Watchmode</CreditLink>.
          This product is not endorsed or certified by Watchmode.
        </p>
      </section>

      <section className="mt-4 rounded-lg border p-6">
        <h2 className="text-lg font-semibold">Stream Channeler Community</h2>
        <p className="mt-4 max-w-xl text-sm text-muted-foreground">
          Links between a website's listing and the title it stands for, issue
          reports, and the corrections made from them are contributed by the
          Stream Channeler Community.
        </p>
      </section>
    </div>
  )
}

// TODO: Validate
function CreditLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="underline hover:text-foreground"
    >
      {children}
    </a>
  )
}
