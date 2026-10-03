// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { Search } from "lucide-react"
import { useState } from "react"

import type { PluginSearchResult } from "@/client"
import { PluginsService, VideoStoreService } from "@/client"
import { ResultCard } from "@/components/Channels/ChannelDetail/Search"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { isLoggedIn } from "@/hooks/useAuth"
import { cn } from "@/lib/utils"

interface TitleMatchesProps {
  titleId: string
  picked: PluginSearchResult | null
  onPick: (result: PluginSearchResult | null) => void
  label?: string
  enabled?: boolean
  notListed?: boolean
  onNotListed?: () => void
}

// TODO: Validate
export function TitleMatches({
  titleId,
  picked,
  onPick,
  label = "Which title should it be?",
  enabled = true,
  notListed = false,
  onNotListed,
}: TitleMatchesProps) {
  const [query, setQuery] = useState("")
  const [term, setTerm] = useState("")
  const loggedIn = isLoggedIn()

  const { data: matches, isFetching: matching } = useQuery({
    queryKey: ["title-matches", titleId],
    queryFn: () => VideoStoreService.getTitleMatches({ titleId }),
    enabled: enabled && Boolean(titleId),
  })

  const { data: searched, isFetching: searching } = useQuery({
    queryKey: ["tmdb-title-search", term],
    queryFn: () => PluginsService.inAppSearch({ query: term }),
    enabled: enabled && loggedIn && term.length > 0,
  })

  const results = term ? (searched?.results ?? []) : (matches ?? [])
  const isFetching = term ? searching : matching

  // TODO: Validate
  const runSearch = () => setTerm(query.trim())

  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      {loggedIn && (
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault()
                  runSearch()
                }
              }}
              placeholder="Search TMDB for another title"
              className="pl-8"
            />
          </div>
          <Button type="button" variant="secondary" onClick={runSearch}>
            Search
          </Button>
        </div>
      )}
      {!loggedIn && (
        <p className="text-sm text-muted-foreground">
          Sign in to search TMDB for a title that is not suggested here.
        </p>
      )}
      <div className="flex flex-wrap gap-3">
        {isFetching && (
          <p className="text-sm text-muted-foreground">Searching…</p>
        )}
        {!isFetching && results.length === 0 && (
          <p className="text-sm text-muted-foreground">
            Nothing on TMDB matches this title.
          </p>
        )}
        {results.map((result) => (
          <div
            key={result.media_identifier ?? result.url}
            className={cn(
              "rounded-md",
              picked === result && "ring-2 ring-primary",
            )}
          >
            <ResultCard
              imageUrl={result.image_url}
              title={result.title}
              subtitle={
                <>
                  {result.media_type}
                  {result.year && ` (${result.year})`}
                </>
              }
              onClick={() => onPick(picked === result ? null : result)}
            />
          </div>
        ))}
        {onNotListed && (
          <button
            type="button"
            onClick={onNotListed}
            className={cn(
              "flex w-36 shrink-0 items-center justify-center rounded-md border p-3 text-center text-sm font-medium transition-colors hover:bg-accent/50",
              notListed && "ring-2 ring-primary",
            )}
          >
            Correct title not listed
          </button>
        )}
      </div>
    </div>
  )
}
