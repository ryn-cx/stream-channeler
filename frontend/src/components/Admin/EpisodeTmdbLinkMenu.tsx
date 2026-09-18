// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Eye, EyeOff, Search } from "lucide-react"
import { useState } from "react"

import type { EpisodeOutput, TmdbEpisodeChoice } from "@/client"
import { EpisodesService } from "@/client"
import { CollapsibleSection } from "@/components/ChannelCommon/CollapsibleSection"
import { AdminZone } from "@/components/Common/AdminZone"
import { EditEpisodeById } from "@/components/Episodes/EditEpisodeById"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { numbering, TmdbEpisodeRow, TmdbPageLink } from "./TmdbEpisodeRow"
import {
  SETTLE_TMDB_MATCH_MUTATION_KEY,
  type SettleTmdbMatchVariables,
  useRereadTmdbMatches,
} from "./tmdbMatchesQuery"
import { type Numbered, numberingAgreement, numberingOf } from "./tmdbNumbering"

type ChoiceOrder = "sequential" | "similarity" | "other"

interface EpisodeTmdbLinkMenuProps {
  episodeId: string
  seasonNumber: number | null | undefined
  episodeNumber: number | null | undefined
  /** Query key of the information the episode was read off. */
  informationQueryKey: unknown[]
  onLinksChanged?: (episode: EpisodeOutput) => void
}

// TODO: Validate
function UsedByDetails({ choice }: { choice: TmdbEpisodeChoice }) {
  const [isOpen, setIsOpen] = useState(false)
  // Carries a default on the server, so the generated type has it as optional.
  const usedBy = choice.used_by ?? []

  return (
    <span className="shrink-0 text-xs">
      <button
        type="button"
        className="text-muted-foreground underline"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
      >
        Already used ({usedBy.length})
      </button>
      {isOpen ? (
        <span className="mt-1 block space-y-0.5">
          {usedBy.map((used) => (
            <span
              key={used.episode.id}
              className="flex items-center gap-1 text-muted-foreground"
            >
              <span className="tabular-nums">
                {numbering(
                  used.season.season_number,
                  used.episode.episode_number,
                )}
              </span>{" "}
              <TmdbPageLink url={used.episode.url}>
                {used.episode.name ?? "Unnamed"}
              </TmdbPageLink>
              <EditEpisodeById episodeId={used.episode.id} />
            </span>
          ))}
        </span>
      ) : null}
    </span>
  )
}

// TODO: Validate
/** Order two numbers, putting the one nothing numbered last. */
function compareNumbers(
  left: number | null | undefined,
  right: number | null | undefined,
): number {
  if (left === right) return 0
  if (left == null) return 1
  if (right == null) return -1
  return left - right
}

// TODO: Validate
/**
 * The TMDB episode an `Episode` stands for, and the ones it could stand for instead.
 *
 * The choices are every episode of every title the title is linked to, which is
 * reached by going from the episode up to its title and back down through the
 * titles that title is linked to. They read in the order the title runs by
 * default, since that is how a website numbers its own episodes, and by how
 * close the names are when the numbering is no help.
 *
 * A title TMDB files an episode under is not always one the title is linked to,
 * so an address can be pasted in as well. It is read by the backend rather than
 * here, which is what imports the title on the way and turns the numbering in
 * an episode's address into the id the episode is linked by.
 */
export function EpisodeTmdbLinkMenu(props: EpisodeTmdbLinkMenuProps) {
  const { user } = useAuth()
  if (!user?.is_superuser) return null

  return (
    <AdminZone className="mt-4">
      <CollapsibleSection title="TMDB episode link">
        <TmdbLinkPicker {...props} />
      </CollapsibleSection>
    </AdminZone>
  )
}

// TODO: Validate
export function TmdbLinkPicker({
  episodeId,
  seasonNumber,
  episodeNumber,
  informationQueryKey,
  onLinksChanged,
}: EpisodeTmdbLinkMenuProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const reread = useRereadTmdbMatches()
  const [order, setOrder] = useState<ChoiceOrder>("sequential")
  const [showUsed, setShowUsed] = useState(false)
  const [nameDraft, setNameDraft] = useState("")
  const [urlDraft, setUrlDraft] = useState("")
  const [searchedName, setSearchedName] = useState<string | null>(null)
  const { data: choices, isLoading } = useQuery({
    queryKey: ["admin-tmdb-choices", episodeId, searchedName],
    queryFn: () =>
      EpisodesService.adminGetTmdbEpisodeChoices({
        episodeId,
        name: searchedName ?? undefined,
      }),
  })

  const linkMutation = useMutation({
    mutationKey: SETTLE_TMDB_MATCH_MUTATION_KEY,
    mutationFn: ({
      tmdbEpisodeId,
    }: SettleTmdbMatchVariables & { tmdbEpisodeId: string }) =>
      EpisodesService.adminLinkEpisodeToTmdb({ episodeId, tmdbEpisodeId }),
    onSuccess: (linked) => {
      showSuccessToast("Episode linked to TMDB")
      queryClient.invalidateQueries({ queryKey: informationQueryKey })
      onLinksChanged?.(linked)
    },
    onError: (error: unknown) => {
      handleError.call(showErrorToast, error as any)
    },
    onSettled: reread,
  })

  const urlMutation = useMutation({
    mutationKey: SETTLE_TMDB_MATCH_MUTATION_KEY,
    mutationFn: ({ episodeIds }: SettleTmdbMatchVariables) =>
      EpisodesService.adminLinkEpisodeByTmdbUrl({
        episodeId: episodeIds[0],
        requestBody: { url: urlDraft },
      }),
    onSuccess: (linked) => {
      showSuccessToast("Episode linked to TMDB")
      setUrlDraft("")
      queryClient.invalidateQueries({ queryKey: informationQueryKey })
      onLinksChanged?.(linked)
    },
    onError: (error: unknown) => {
      handleError.call(showErrorToast, error as any)
    },
    onSettled: reread,
  })

  const episodeNumbering: Numbered = {
    season_number: seasonNumber ?? null,
    episode_number: episodeNumber ?? null,
    absolute_number: null,
  }

  // TODO: Validate
  const agreementWith = (choice: TmdbEpisodeChoice) =>
    numberingAgreement(numberingOf(choice), episodeNumbering)

  const wanted = nameDraft.trim().toLowerCase()
  const isSearch = searchedName !== null

  const offered = choices ?? []
  const inScope = offered.filter(
    (choice) =>
      (isSearch || (choice.from_title === false) === (order === "other")) &&
      (showUsed || !choice.already_used) &&
      (isSearch ||
        wanted.length === 0 ||
        (choice.episode.name ?? "").toLowerCase().includes(wanted) ||
        (choice.title.name ?? "").toLowerCase().includes(wanted)),
  )

  // TODO: Validate
  const searchEverything = () => {
    const asked = nameDraft.trim()
    if (asked.length === 0) return
    setSearchedName(asked)
  }

  const ordered = [...inScope].sort(
    (left: TmdbEpisodeChoice, right: TmdbEpisodeChoice) => {
      if (order !== "sequential") return right.similarity - left.similarity
      return (
        compareNumbers(left.season.season_number, right.season.season_number) ||
        compareNumbers(
          left.episode.episode_number,
          right.episode.episode_number,
        )
      )
    },
  )

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <Input
          value={nameDraft}
          onChange={(event) => {
            setNameDraft(event.target.value)
            if (event.target.value.trim().length === 0) setSearchedName(null)
          }}
          onKeyDown={(event) => {
            if (event.key !== "Enter") return
            event.preventDefault()
            searchEverything()
          }}
          placeholder="Filter by name"
          aria-label="Filter the episodes below by name"
          className="w-40 min-w-0"
        />
        <Button
          type="button"
          variant="outline"
          disabled={nameDraft.trim().length === 0}
          onClick={searchEverything}
        >
          <Search />
          Search every title
        </Button>
        <Tabs
          value={order}
          onValueChange={(value) => setOrder(value as ChoiceOrder)}
        >
          <TabsList>
            <TabsTrigger value="sequential">Sequential</TabsTrigger>
            <TabsTrigger value="similarity">Closest name</TabsTrigger>
            <TabsTrigger value="other">Other Title Name Matches</TabsTrigger>
          </TabsList>
        </Tabs>
        <Button
          type="button"
          variant="outline"
          onClick={() => setShowUsed(!showUsed)}
        >
          {showUsed ? <EyeOff /> : <Eye />}
          {showUsed ? "Hide already used" : "Title already used"}
        </Button>
      </div>

      <div className="max-h-96 overflow-y-auto rounded-lg border">
        {isSearch ? (
          <p className="border-b px-3 py-2 text-xs text-muted-foreground">
            Every TMDB episode named “{searchedName}”, whichever title it
            belongs to.
          </p>
        ) : null}
        {isLoading ? (
          <p className="p-4 text-sm text-muted-foreground">Loading…</p>
        ) : ordered.length === 0 ? (
          <p className="p-4 text-sm text-muted-foreground">
            {isSearch
              ? offered.length === 0
                ? "No TMDB episode anywhere in the database is named that."
                : "Every TMDB episode named that is already used by another episode of this title."
              : order === "other"
                ? "No TMDB episode of any other title reads close enough to this name."
                : offered.length === 0
                  ? "No TMDB episodes to choose from. Paste the address of the episode on TMDB to link it and read its title in."
                  : wanted.length > 0
                    ? "No TMDB episode of this title is named that."
                    : "Every TMDB episode of this title is already used by another episode of this title."}
          </p>
        ) : (
          ordered.map((choice) => (
            <TmdbEpisodeRow
              key={choice.episode.id}
              record={choice}
              absoluteNumber={choice.absolute_number}
              disagreement={agreementWith(choice)}
              middle={
                choice.already_used ? <UsedByDetails choice={choice} /> : null
              }
              className={
                choice.from_title === false
                  ? "text-blue-600 dark:text-blue-400"
                  : undefined
              }
              trailing={
                <>
                  <span className="shrink-0 tabular-nums text-muted-foreground">
                    {Math.round(choice.similarity * 100)}%
                  </span>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="shrink-0"
                    disabled={linkMutation.isPending}
                    onClick={() =>
                      linkMutation.mutate({
                        episodeIds: [episodeId],
                        tmdbEpisodeId: choice.episode.id,
                      })
                    }
                  >
                    Link
                  </Button>
                </>
              }
            />
          ))
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Input
          value={urlDraft}
          onChange={(event) => setUrlDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key !== "Enter") return
            event.preventDefault()
            if (urlDraft.trim().length === 0 || urlMutation.isPending) return
            urlMutation.mutate({ episodeIds: [episodeId] })
          }}
          placeholder="themoviedb.org address of a film or of one episode"
          aria-label="TMDB address"
          className="min-w-48 flex-1"
        />
        <Button
          type="button"
          variant="outline"
          disabled={urlDraft.trim().length === 0 || urlMutation.isPending}
          onClick={() => urlMutation.mutate({ episodeIds: [episodeId] })}
        >
          Link by address
        </Button>
      </div>
    </div>
  )
}
