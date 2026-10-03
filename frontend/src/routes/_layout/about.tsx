// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Check, Minus, X } from "lucide-react"
import type { ReactNode } from "react"
import Markdown from "react-markdown"
import { type CatalogSupport, PluginsService } from "@/client"
import { SourceOptionLabel } from "@/components/Common/SourceOptionLabel"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"

export const Route = createFileRoute("/_layout/about")({
  component: About,
  head: () => ({
    meta: [{ title: "About - Stream Channeler" }],
  }),
})

// TODO: Validate
function About() {
  return (
    <div className="container mx-auto max-w-3xl px-4 py-16">
      <h1 className="text-4xl font-bold tracking-tight">About</h1>

      <PluginsSection />

      <section className="mt-4 rounded-lg border p-6">
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
          Titles, seasons, episodes, artwork, and other information is from{" "}
          <AboutLink href="https://www.themoviedb.org">TMDB</AboutLink>.
        </p>
      </section>

      <section className="mt-4 rounded-lg border p-6">
        <h2 className="text-lg font-semibold">JustWatch</h2>
        <p className="mt-4 max-w-xl text-sm text-muted-foreground">
          This product uses the TMDB API to access{" "}
          <AboutLink href="https://www.justwatch.com">JustWatch</AboutLink>'s
          watch provider information but is not endorsed or certified by
          JustWatch.
        </p>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          When data from JustWatch is used it will be explicitly stated on that
          page.
        </p>
      </section>

      <section className="mt-4 rounded-lg border p-6">
        <h2 className="text-lg font-semibold">Stream Channeler Community</h2>
        <p className="mt-4 max-w-xl text-sm text-muted-foreground">
          Community contributions help improve the accuracy and completeness of
          the information provided by Stream Channeler by reporting incorrect
          information and suggesting corrections.
        </p>
      </section>
    </div>
  )
}

// TODO: Validate
function PluginsSection() {
  const { data: plugins } = useQuery({
    queryKey: ["plugin-support-information"],
    queryFn: () => PluginsService.supportInformation(),
  })

  return (
    <section className="mt-8 rounded-lg border p-6">
      <h2 className="text-lg font-semibold">Supported Sites</h2>
      <div className="mt-4">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Plugin</TableHead>
              <TableHead>Full catalog</TableHead>
              <TableHead>Known issues</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(plugins ?? []).map((plugin) => (
              <TableRow key={plugin.name}>
                <TableCell className="align-top">
                  <SourceOptionLabel
                    name={plugin.name}
                    faviconUrl={plugin.favicon_url}
                  />
                </TableCell>
                <TableCell className="align-top">
                  <CatalogSupportLabel support={plugin.catalog_support} />
                </TableCell>
                <TableCell className="whitespace-normal align-top text-muted-foreground">
                  {plugin.known_issues ? (
                    <Markdown
                      components={{
                        a: ({ href, children }) => (
                          <AboutLink href={href ?? ""}>{children}</AboutLink>
                        ),
                      }}
                    >
                      {plugin.known_issues}
                    </Markdown>
                  ) : null}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </section>
  )
}

// TODO: Validate
function CatalogSupportLabel({ support }: { support: CatalogSupport }) {
  const { icon: Icon, className } = {
    Yes: { icon: Check, className: "text-green-500" },
    Mostly: { icon: Minus, className: "text-amber-500" },
    No: { icon: X, className: "text-red-500" },
  }[support]

  return (
    <span className="flex items-center gap-2">
      <Icon className={cn("size-4 shrink-0", className)} />
      {support}
    </span>
  )
}

// TODO: Validate
function AboutLink({ href, children }: { href: string; children: ReactNode }) {
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
