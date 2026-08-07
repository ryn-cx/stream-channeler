// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { useState } from "react"

import {
  EpisodesService,
  type TmdbEpisodeChoice,
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

type ChoiceOrder = "episode" | "similarity"

/** "S1E1", or as much of it as TMDB numbered the episode with. */
function numbering(
  seasonNumber: number | null,
  episodeNumber: number | null,
): string {
  return `S${seasonNumber ?? "?"}E${episodeNumber ?? "?"}`
}

/** Order two numbers, putting the one nothing numbered last. */
function compareNumbers(left: number | null, right: number | null): number {
  if (left === right) return 0
  if (left === null) return 1
  if (right === null) return -1
  return left - right
}

/**
 * Whether a choice is numbered the same as the episode being linked.
 *
 * Either numbering counts, since a website that restarts its numbering each
 * season agrees with TMDB on the season and episode, and one that runs straight
 * through agrees on how far into the title the episode is.
 */
function isNumberedTheSame(
  episode: UnmatchedEpisodeOutput,
  choice: TmdbEpisodeChoice,
): boolean {
  const seasonAndEpisodeAgree =
    episode.season_number !== null &&
    episode.episode_number !== null &&
    episode.season_number === choice.season_number &&
    episode.episode_number === choice.episode_number
  const absoluteAgrees =
    episode.absolute_number !== null &&
    episode.absolute_number === choice.absolute_number
  return seasonAndEpisodeAgree || absoluteAgrees
}

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
  onPick: (tmdbEpisodeId: number) => void
  isLinking: boolean
}) {
  const [search, setSearch] = useState("")
  const [order, setOrder] = useState<ChoiceOrder>("episode")

  const { data: choices } = useQuery({
    queryKey: ["admin-tmdb-choices", episode.id],
    queryFn: () =>
      EpisodesService.adminGetTmdbEpisodeChoices({ episodeId: episode.id }),
    enabled: isOpen,
  })

  const query = search.trim().toLowerCase()
  const matching = (choices ?? []).filter((choice) => {
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
        </div>

        <div className="max-h-96 overflow-y-auto rounded-lg border">
          {!choices ? (
            <p className="p-4 text-sm text-muted-foreground">Loading…</p>
          ) : ordered.length === 0 ? (
            <p className="p-4 text-sm text-muted-foreground">
              No TMDB episodes to choose from.
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
                  <span className="shrink-0 tabular-nums text-muted-foreground">
                    {Math.round(choice.similarity * 100)}%
                  </span>
                </Button>
              )
            })
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
