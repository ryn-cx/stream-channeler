// TODO: Validate
import {
  type QueryKey,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query"
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
import {
  CanonicalEpisodeRow,
  numbering,
  TmdbPageLink,
} from "./CanonicalEpisodeRow"
import { useSettleTmdbMatch } from "./tmdbMatchesQuery"
import { type Numbered, numberingAgreement, numberingOf } from "./tmdbNumbering"

type ChoiceOrder = "sequential" | "similarity" | "other"

/** Every list of choices as it read before one of them was linked. */
type DroppedChoices = Array<[QueryKey, TmdbEpisodeChoice[] | undefined]>

interface EpisodeTmdbLinkMenuProps {
  episodeId: string
  seasonNumber: number | null | undefined
  episodeNumber: number | null | undefined
  /** Query key of the information the episode was read off. */
  informationQueryKey: unknown[]
  onLinksChanged?: (episode: EpisodeOutput) => void
}

// TODO: Validate
/**
 * Which of the show's own episodes are on this TMDB episode already.
 *
 * A choice being spoken for is the reason it is worth passing over, so which
 * episode spoke for it is the next thing anybody asks - most often because that
 * one is the mistake, not this one. It is asked for rather than shown outright,
 * since a list under every used choice would bury the ones going spare.
 */
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
 * The choices are every episode of every title the show is linked to, which is
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
    <AdminZone className="mt-4">
      <CollapsibleSection title="TMDB episode link">
        <TmdbLinkPicker {...props} />
      </CollapsibleSection>
    </AdminZone>
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
export function TmdbLinkPicker({
  episodeId,
  seasonNumber,
  episodeNumber,
  informationQueryKey,
  onLinksChanged,
}: EpisodeTmdbLinkMenuProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const { settle, restore, reread } = useSettleTmdbMatch()
  const [order, setOrder] = useState<ChoiceOrder>("sequential")
  // The episodes still going spare are what a title is usually missing, so they
  // are what is offered until the whole title is asked for.
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

  // TODO: Validate
  const dropChoice = async (canonicalEpisodeId: string) => {
    const choicesKey = ["admin-tmdb-choices", episodeId]
    await queryClient.cancelQueries({ queryKey: choicesKey })
    const previous = queryClient.getQueriesData<TmdbEpisodeChoice[]>({
      queryKey: choicesKey,
    })
    queryClient.setQueriesData<TmdbEpisodeChoice[]>(
      { queryKey: choicesKey },
      (offered) =>
        offered?.filter((choice) => choice.episode.id !== canonicalEpisodeId),
    )
    return previous
  }

  // TODO: Validate
  const restoreChoices = (previous: DroppedChoices | undefined) => {
    for (const [queryKey, offered] of previous ?? []) {
      queryClient.setQueryData(queryKey, offered)
    }
  }

  const linkMutation = useMutation({
    mutationFn: (canonicalEpisodeId: string) =>
      EpisodesService.adminLinkEpisodeToTmdb({ episodeId, canonicalEpisodeId }),
    onMutate: async (canonicalEpisodeId: string) => ({
      matches: await settle(episodeId),
      choices: await dropChoice(canonicalEpisodeId),
    }),
    onSuccess: (linked) => {
      showSuccessToast("Episode linked to TMDB")
      queryClient.invalidateQueries({ queryKey: informationQueryKey })
      onLinksChanged?.(linked)
    },
    onError: (error: unknown, _variables, previous) => {
      restore(previous?.matches)
      restoreChoices(previous?.choices)
      handleError.call(showErrorToast, error as any)
    },
    onSettled: reread,
  })

  const urlMutation = useMutation({
    mutationFn: () =>
      EpisodesService.adminLinkEpisodeByTmdbUrl({
        episodeId,
        requestBody: { url: urlDraft },
      }),
    onMutate: () => settle(episodeId),
    onSuccess: (linked) => {
      showSuccessToast("Episode linked to TMDB")
      setUrlDraft("")
      queryClient.invalidateQueries({ queryKey: informationQueryKey })
      onLinksChanged?.(linked)
    },
    onError: (error: unknown, _variables, previous) => {
      restore(previous)
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
      (isSearch || (choice.from_show === false) === (order === "other")) &&
      (showUsed || !choice.already_used) &&
      (isSearch ||
        wanted.length === 0 ||
        (choice.episode.name ?? "").toLowerCase().includes(wanted) ||
        (choice.show.name ?? "").toLowerCase().includes(wanted)),
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
          Search every show
        </Button>
        <Tabs
          value={order}
          onValueChange={(value) => setOrder(value as ChoiceOrder)}
        >
          <TabsList>
            <TabsTrigger value="sequential">Sequential</TabsTrigger>
            <TabsTrigger value="similarity">Closest name</TabsTrigger>
            <TabsTrigger value="other">Other Show Name Matches</TabsTrigger>
          </TabsList>
        </Tabs>
        <Button
          type="button"
          variant="outline"
          onClick={() => setShowUsed(!showUsed)}
        >
          {showUsed ? <EyeOff /> : <Eye />}
          {showUsed ? "Hide already used" : "Show already used"}
        </Button>
      </div>

      <div className="max-h-96 overflow-y-auto rounded-lg border">
        {isSearch ? (
          <p className="border-b px-3 py-2 text-xs text-muted-foreground">
            Every TMDB episode named “{searchedName}”, whichever show it belongs
            to.
          </p>
        ) : null}
        {isLoading ? (
          <p className="p-4 text-sm text-muted-foreground">Loading…</p>
        ) : ordered.length === 0 ? (
          <p className="p-4 text-sm text-muted-foreground">
            {isSearch
              ? offered.length === 0
                ? "No TMDB episode anywhere in the database is named that."
                : "Every TMDB episode named that is already used by another episode of this show."
              : order === "other"
                ? "No TMDB episode of any other show reads close enough to this name."
                : offered.length === 0
                  ? "No TMDB episodes to choose from. Paste the address of the episode on TMDB to link it and read its title in."
                  : wanted.length > 0
                    ? "No TMDB episode of this title is named that."
                    : "Every TMDB episode of this title is already used by another episode of this show."}
          </p>
        ) : (
          ordered.map((choice) => (
            <CanonicalEpisodeRow
              key={choice.episode.id}
              record={choice}
              absoluteNumber={choice.absolute_number}
              disagreement={agreementWith(choice)}
              middle={
                choice.already_used ? <UsedByDetails choice={choice} /> : null
              }
              className={
                choice.from_show === false
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
                    onClick={() => linkMutation.mutate(choice.episode.id)}
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
            urlMutation.mutate()
          }}
          placeholder="themoviedb.org address of a film or of one episode"
          aria-label="TMDB address"
          className="min-w-48 flex-1"
        />
        <Button
          type="button"
          variant="outline"
          disabled={urlDraft.trim().length === 0 || urlMutation.isPending}
          onClick={() => urlMutation.mutate()}
        >
          Link by address
        </Button>
      </div>
    </div>
  )
}
