// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { useState } from "react"

import {
  EpisodesService,
  type MediaType,
  type UnmatchedEpisodeOutput,
} from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { cn } from "@/lib/utils"
import { isNumberedTheSame } from "./tmdbNumbering"

type ChoiceOrder = "episode" | "similarity"
type ChoiceScope = "unused" | "all"

// TODO: Validate
/** "S1E1", or as much of it as TMDB numbered the episode with. */
function numbering(
  seasonNumber: number | null,
  episodeNumber: number | null,
): string {
  return `S${seasonNumber ?? "?"}E${episodeNumber ?? "?"}`
}

/** The id in a TMDB address, so a page can be pasted in rather than read off. */
const TMDB_URL_ID = /themoviedb\.org\/(?:tv|movie)\/(\d+)/

// TODO: Validate
/** Return the TMDB id a URL or a bare number names, or null where it names none. */
function parseTmdbId(value: string): number | null {
  const trimmed = value.trim()
  const inUrl = TMDB_URL_ID.exec(trimmed)
  const digits = inUrl ? inUrl[1] : trimmed
  return /^\d+$/.test(digits) ? Number(digits) : null
}

// TODO: Validate
/** Order two numbers, putting the one nothing numbered last. */
function compareNumbers(left: number | null, right: number | null): number {
  if (left === right) return 0
  if (left === null) return 1
  if (right === null) return -1
  return left - right
}

// TODO: Validate
/**
 * Every TMDB episode of a title, in the order the title runs, to pick one from.
 *
 * Each is shown by its season and episode number and by how far into the whole
 * title it is, since a website that numbers a title straight through names the
 * same episode by the second of those and not the first. Whichever is numbered
 * as the episode being linked is held at the top and picked out, and the list
 * can be read by how close the names are instead when the numbering is no help.
 */
export function TmdbEpisodePickerDialog({
  episode,
  isOpen,
  onOpenChange,
  onPick,
  isLinking,
}: {
  episode: UnmatchedEpisodeOutput
  isOpen: boolean
  onOpenChange: (isOpen: boolean) => void
  onPick: (tmdbEpisodeId: number, mediaType?: MediaType) => void
  isLinking: boolean
}) {
  const [search, setSearch] = useState("")
  const [movieId, setMovieId] = useState("")
  const [seriesInput, setSeriesInput] = useState("")
  // The title whose episodes are being read, where it is not the one the show
  // is linked to.
  const [loadedSeriesId, setLoadedSeriesId] = useState<number | null>(null)
  const [order, setOrder] = useState<ChoiceOrder>("episode")
  // The episodes still going spare are what a title is usually missing, so they
  // are what is offered until the whole title is asked for.
  const [scope, setScope] = useState<ChoiceScope>("unused")

  const { data: choices } = useQuery({
    queryKey: ["admin-tmdb-choices", episode.id, loadedSeriesId],
    queryFn: () =>
      EpisodesService.adminGetTmdbEpisodeChoices({
        episodeId: episode.id,
        tmdbShowId: loadedSeriesId,
      }),
    enabled: isOpen,
  })

  const query = search.trim().toLowerCase()
  const inScope = (choices ?? []).filter(
    (choice) => scope === "all" || !choice.already_used,
  )
  const matching = inScope.filter((choice) => {
    if (!query) return true
    return [
      choice.name ?? "",
      numbering(choice.season_number, choice.episode_number),
      `#${choice.absolute_number ?? ""}`,
      String(choice.tmdb_episode_id),
    ]
      .join(" ")
      .toLowerCase()
      .includes(query)
  })

  const typedSeriesId = parseTmdbId(seriesInput)
  const typedMovieId = parseTmdbId(movieId)

  const ordered = [...matching].sort((left, right) => {
    const numbered =
      Number(isNumberedTheSame(episode, right)) -
      Number(isNumberedTheSame(episode, left))
    if (numbered !== 0) return numbered
    if (order === "similarity") return right.similarity - left.similarity
    return (
      compareNumbers(left.season_number, right.season_number) ||
      compareNumbers(left.episode_number, right.episode_number)
    )
  })

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Choose a TMDB episode</DialogTitle>
          <DialogDescription>
            {episode.name ?? "Unnamed"} —{" "}
            {numbering(episode.season_number, episode.episode_number)}
            {episode.absolute_number ? ` · #${episode.absolute_number}` : ""}
          </DialogDescription>
        </DialogHeader>

        <form
          className="flex items-center gap-2"
          onSubmit={(event) => {
            event.preventDefault()
            setLoadedSeriesId(typedSeriesId)
          }}
        >
          <Input
            value={seriesInput}
            onChange={(event) => setSeriesInput(event.target.value)}
            placeholder="TMDB series URL or id, to read another title's episodes"
            aria-label="TMDB series URL or id"
            className="min-w-48 flex-1"
          />
          <Button
            type="submit"
            variant="outline"
            disabled={typedSeriesId === null}
          >
            Load series
          </Button>
          {loadedSeriesId === null ? null : (
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setLoadedSeriesId(null)
                setSeriesInput("")
              }}
            >
              Back to linked title
            </Button>
          )}
        </form>

        <div className="flex flex-wrap items-center gap-2">
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Filter by name, S1E1, #12 or id"
            aria-label="Filter episodes"
            className="min-w-48 flex-1"
          />
          <Tabs
            value={order}
            onValueChange={(value) => setOrder(value as ChoiceOrder)}
          >
            <TabsList>
              <TabsTrigger value="episode">Episode number</TabsTrigger>
              <TabsTrigger value="similarity">Name match</TabsTrigger>
            </TabsList>
          </Tabs>
          <Tabs
            value={scope}
            onValueChange={(value) => setScope(value as ChoiceScope)}
          >
            <TabsList>
              <TabsTrigger value="unused">Not yet used</TabsTrigger>
              <TabsTrigger value="all">All episodes</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        <div className="max-h-96 overflow-y-auto rounded-lg border">
          {!choices ? (
            <p className="p-4 text-sm text-muted-foreground">Loading…</p>
          ) : ordered.length === 0 ? (
            <p className="p-4 text-sm text-muted-foreground">
              {scope === "unused" && inScope.length !== (choices?.length ?? 0)
                ? "Every TMDB episode of this title is already used by another episode of this show."
                : "No TMDB episodes to choose from."}
            </p>
          ) : (
            ordered.map((choice) => {
              const numberedTheSame = isNumberedTheSame(episode, choice)
              return (
                <Button
                  key={choice.tmdb_episode_id}
                  variant="ghost"
                  disabled={isLinking}
                  className="h-auto w-full justify-start gap-3 rounded-none px-3 py-2 text-left"
                  onClick={() => onPick(choice.tmdb_episode_id)}
                >
                  <span
                    className={cn(
                      "w-24 shrink-0 tabular-nums",
                      numberedTheSame
                        ? "text-destructive"
                        : "text-muted-foreground",
                    )}
                  >
                    {numbering(choice.season_number, choice.episode_number)}
                    {choice.absolute_number
                      ? ` · #${choice.absolute_number}`
                      : ""}
                  </span>
                  <span className="flex-1 whitespace-normal wrap-break-word">
                    {choice.name ?? "Unnamed"}
                  </span>
                  {choice.already_used ? (
                    <span className="shrink-0 text-xs text-muted-foreground">
                      Already used
                    </span>
                  ) : null}
                  <span className="shrink-0 tabular-nums text-muted-foreground">
                    {Math.round(choice.similarity * 100)}%
                  </span>
                </Button>
              )
            })
          )}
        </div>

        <form
          className="flex items-center gap-2"
          onSubmit={(event) => {
            event.preventDefault()
            if (typedMovieId !== null) {
              onPick(typedMovieId, "movie")
            }
          }}
        >
          <Input
            value={movieId}
            onChange={(event) => setMovieId(event.target.value)}
            inputMode="numeric"
            placeholder="TMDB movie id"
            aria-label="TMDB movie id"
            className="min-w-48 flex-1"
          />
          <Button
            type="submit"
            variant="outline"
            disabled={typedMovieId === null || isLinking}
          >
            Link movie
          </Button>
        </form>
        <p className="text-xs text-muted-foreground">
          A movie is one record, so its id is enough to read it in and link to
          it on its own. A series episode is numbered apart from its series, so
          one is reached by loading the series above rather than by its id.
        </p>
      </DialogContent>
    </Dialog>
  )
}
