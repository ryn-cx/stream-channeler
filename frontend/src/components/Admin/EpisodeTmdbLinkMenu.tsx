// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Eye, EyeOff, Unlink } from "lucide-react"
import { useState } from "react"

import type { TmdbEpisodeChoice } from "@/client"
import { EpisodesService } from "@/client"
import { CollapsibleSection } from "@/components/ChannelCommon/CollapsibleSection"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { cn } from "@/lib/utils"
import { handleError } from "@/utils"
import { type Numbered, numberingAgreement } from "./tmdbNumbering"

type ChoiceOrder = "sequential" | "similarity"

interface EpisodeTmdbLinkMenuProps {
  episodeId: string
  name: string | null
  seasonNumber: number | null
  episodeNumber: number | null
  /** Query key of the information the episode was read off. */
  informationQueryKey: unknown[]
}

// TODO: Validate
/** "S1E1", or as much of it as the record was numbered with. */
function numbering(
  seasonNumber: number | null,
  episodeNumber: number | null,
): string {
  return `S${seasonNumber ?? "?"}E${episodeNumber ?? "?"}`
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
 * The TMDB episode an `Episode` stands for, and the ones it could stand for instead.
 *
 * The choices are every episode of every title the show is a copy of, which is
 * reached by going from the episode up to its show and back down through the
 * titles that show is linked to. They read in the order the title runs by
 * default, since that is how a website numbers its own episodes, and by how
 * close the names are when the numbering is no help.
 *
 * A title TMDB files an episode under is not always one the show is linked to,
 * so an address can be pasted in as well. It is read by the backend rather than
 * here, which is what imports the title on the way and turns the numbering in
 * an episode's address into the id the episode is linked by.
 */
export function EpisodeTmdbLinkMenu(props: EpisodeTmdbLinkMenuProps) {
  const { user } = useAuth()
  if (!user?.is_superuser) return null

  return (
    <div className="mt-4">
      <CollapsibleSection title="TMDB episode link">
        <TmdbLinkPicker {...props} />
      </CollapsibleSection>
    </div>
  )
}

// TODO: Validate
/**
 * The choices themselves, mounted only once the menu is opened.
 *
 * Every episode of every linked title is read to build the list, which is far
 * more than an episode's own page is worth costing, so nothing is asked for
 * until somebody goes looking.
 */
function TmdbLinkPicker({
  episodeId,
  name,
  seasonNumber,
  episodeNumber,
  informationQueryKey,
}: EpisodeTmdbLinkMenuProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const [order, setOrder] = useState<ChoiceOrder>("similarity")
  // The episodes still going spare are what a title is usually missing, so they
  // are what is offered until the whole title is asked for.
  const [showUsed, setShowUsed] = useState(false)
  const [urlDraft, setUrlDraft] = useState("")
  const { data: choices, isLoading } = useQuery({
    queryKey: ["admin-tmdb-choices", episodeId],
    queryFn: () => EpisodesService.adminGetTmdbEpisodeChoices({ episodeId }),
  })

  const linkMutation = useMutation({
    mutationFn: (canonicalEpisodeId: string) =>
      EpisodesService.adminLinkEpisodeToTmdb({ episodeId, canonicalEpisodeId }),
    onSuccess: () => {
      showSuccessToast("Episode linked to TMDB")
      queryClient.invalidateQueries({ queryKey: informationQueryKey })
      queryClient.invalidateQueries({ queryKey: ["admin-tmdb-choices"] })
    },
    onError: (error: unknown) => handleError.call(showErrorToast, error as any),
  })

  const unlinkMutation = useMutation({
    mutationFn: () => EpisodesService.adminUnlinkEpisodeFromTmdb({ episodeId }),
    onSuccess: () => {
      showSuccessToast("Episode unlinked from TMDB")
      queryClient.invalidateQueries({ queryKey: informationQueryKey })
      queryClient.invalidateQueries({ queryKey: ["admin-tmdb-choices"] })
    },
    onError: (error: unknown) => handleError.call(showErrorToast, error as any),
  })

  const urlMutation = useMutation({
    mutationFn: () =>
      EpisodesService.adminLinkEpisodeByTmdbUrl({
        episodeId,
        requestBody: { url: urlDraft },
      }),
    onSuccess: () => {
      showSuccessToast("Episode linked to TMDB")
      setUrlDraft("")
      queryClient.invalidateQueries({ queryKey: informationQueryKey })
      queryClient.invalidateQueries({ queryKey: ["admin-tmdb-choices"] })
    },
    onError: (error: unknown) => handleError.call(showErrorToast, error as any),
  })

  const episodeNumbering: Numbered = {
    season_number: seasonNumber,
    episode_number: episodeNumber,
    absolute_number: null,
  }

  // TODO: Validate
  const agreementWith = (choice: TmdbEpisodeChoice) =>
    numberingAgreement(choice, episodeNumbering)

  const inScope = (choices ?? []).filter(
    (choice) => showUsed || !choice.already_used,
  )

  const ordered = [...inScope].sort(
    (left: TmdbEpisodeChoice, right: TmdbEpisodeChoice) => {
      if (order === "similarity") return right.similarity - left.similarity
      return (
        compareNumbers(left.season_number, right.season_number) ||
        compareNumbers(left.episode_number, right.episode_number)
      )
    },
  )

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">
        {name ?? "Unnamed"} — {numbering(seasonNumber, episodeNumber)}
      </p>

      <div className="flex flex-wrap items-center gap-2">
        <Tabs
          value={order}
          onValueChange={(value) => setOrder(value as ChoiceOrder)}
        >
          <TabsList>
            <TabsTrigger value="similarity">Closest name</TabsTrigger>
            <TabsTrigger value="sequential">Sequential</TabsTrigger>
          </TabsList>
        </Tabs>
        <Button variant="outline" onClick={() => setShowUsed(!showUsed)}>
          {showUsed ? <EyeOff /> : <Eye />}
          {showUsed ? "Hide already used" : "Show already used"}
        </Button>
      </div>

      <div className="max-h-96 overflow-y-auto rounded-lg border">
        {isLoading ? (
          <p className="p-4 text-sm text-muted-foreground">Loading…</p>
        ) : ordered.length === 0 ? (
          <p className="p-4 text-sm text-muted-foreground">
            {(choices ?? []).length === 0
              ? "No TMDB episodes to choose from. Paste the address of the episode on TMDB to link it and read its title in."
              : "Every TMDB episode of this title is already used by another episode of this show."}
          </p>
        ) : (
          ordered.map((choice) => (
            <div
              key={choice.tmdb_episode_id}
              className="flex items-center gap-3 border-b px-3 py-2 text-sm last:border-b-0"
            >
              <span className="w-24 shrink-0 tabular-nums">
                <span
                  className={
                    agreementWith(choice).seasonAndEpisode
                      ? "text-destructive"
                      : "text-muted-foreground"
                  }
                >
                  {numbering(choice.season_number, choice.episode_number)}
                </span>
                <span
                  className={cn(
                    "block text-xs",
                    agreementWith(choice).absolute
                      ? "text-destructive"
                      : "text-muted-foreground",
                  )}
                >
                  {choice.absolute_number === null
                    ? "N/A"
                    : `#${choice.absolute_number}`}
                </span>
              </span>
              <span className="flex-1 whitespace-normal wrap-break-word">
                {choice.name}
                <span className="block text-xs text-muted-foreground">
                  {choice.show_name}
                </span>
              </span>
              {choice.already_used ? (
                <span className="shrink-0 text-xs text-muted-foreground">
                  Already used
                </span>
              ) : null}
              <span className="shrink-0 tabular-nums text-muted-foreground">
                {Math.round(choice.similarity * 100)}%
              </span>
              <Button
                variant="outline"
                size="sm"
                className="shrink-0"
                disabled={linkMutation.isPending}
                onClick={() => linkMutation.mutate(choice.canonical_episode_id)}
              >
                Link
              </Button>
            </div>
          ))
        )}
      </div>

      <form
        className="flex flex-wrap items-center gap-2"
        onSubmit={(event) => {
          event.preventDefault()
          urlMutation.mutate()
        }}
      >
        <Input
          value={urlDraft}
          onChange={(event) => setUrlDraft(event.target.value)}
          placeholder="themoviedb.org address of a film or of one episode"
          aria-label="TMDB address"
          className="min-w-48 flex-1"
        />
        <Button
          type="submit"
          variant="outline"
          disabled={urlDraft.trim().length === 0 || urlMutation.isPending}
        >
          Link by address
        </Button>
      </form>

      <Button
        variant="outline"
        className="self-start"
        disabled={unlinkMutation.isPending}
        onClick={() => unlinkMutation.mutate()}
      >
        <Unlink />
        Unlink from TMDB
      </Button>
    </div>
  )
}
