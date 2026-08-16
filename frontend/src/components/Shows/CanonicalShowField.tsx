// TODO: Validate
import {
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query"
import { X } from "lucide-react"
import { useState } from "react"

import {
  type CanonicalShowOutput,
  CanonicalShowsService,
  ShowsService,
} from "@/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

/** How many titles a search offers, which is as many as the box holds. */
const SEARCH_RESULT_COUNT = 10

/** How short a search is before it matches most of the catalogue. */
const SEARCH_MINIMUM_LENGTH = 2

interface CanonicalShowFieldProps {
  showId: string
  canonicalShowIds: string[]
  /** Only asked for while the form is open, since each is a query of its own. */
  enabled: boolean
}

// TODO: Validate
function CanonicalShowName({ show }: { show: CanonicalShowOutput }) {
  return (
    <span className="flex-1 whitespace-normal wrap-break-word">
      {show.tmdb_url ? (
        <a
          href={show.tmdb_url}
          target="_blank"
          rel="noopener noreferrer"
          className="hover:underline"
        >
          {show.name ?? "Unnamed"}
        </a>
      ) : (
        (show.name ?? "Unnamed")
      )}
      <span className="block text-xs text-muted-foreground">
        {show.key}
        {show.year ? ` — ${show.year}` : ""}
      </span>
    </span>
  )
}

// TODO: Validate
/**
 * Which canonical shows this row stands for, and the choosing of another.
 *
 * A row is linked to the titles it is a copy of by the import that read it,
 * which is a guess made off the name and the year and is wrong often enough to
 * be worth settling by hand. Choosing here adds to what the row already stands
 * for rather than replacing it, since one page holding two titles - a channel
 * whose uploads are two series, a sequel sold as another season - is a thing
 * websites do. Taking one off is the X beside it.
 *
 * The links are written as soon as they are chosen rather than with the rest of
 * the form: they are rows of their own, and what they drag along - every episode
 * read again against the titles left - is not something the show's own columns
 * do.
 */
export function CanonicalShowField({
  showId,
  canonicalShowIds,
  enabled,
}: CanonicalShowFieldProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const [search, setSearch] = useState("")

  const linkedQueries = useQueries({
    queries: canonicalShowIds.map((canonicalShowId) => ({
      queryKey: ["canonical-show", canonicalShowId],
      queryFn: () =>
        CanonicalShowsService.getCanonicalShowById({ canonicalShowId }),
      enabled,
    })),
  })
  const linked = linkedQueries
    .map((query) => query.data)
    .filter((show) => show !== undefined)

  const { data: results, isFetching } = useQuery({
    queryKey: ["canonical-shows", "search", search],
    queryFn: () =>
      CanonicalShowsService.getCanonicalShows({
        filterOptions: JSON.stringify([{ id: "name", value: search }]),
        limit: SEARCH_RESULT_COUNT,
      }),
    enabled: enabled && search.trim().length > SEARCH_MINIMUM_LENGTH,
  })

  // TODO: Validate
  const rereadShow = () => {
    queryClient.invalidateQueries({ queryKey: ["shows"] })
    queryClient.invalidateQueries({ queryKey: ["show-information", showId] })
    queryClient.invalidateQueries({ queryKey: ["canonical-show"] })
  }

  const linkMutation = useMutation({
    mutationFn: (chosenId: string) =>
      ShowsService.adminLinkShowToCanonical({
        showId,
        canonicalShowId: chosenId,
      }),
    onSuccess: () => {
      showSuccessToast("Show linked to canonical show")
      setSearch("")
      rereadShow()
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  const unlinkMutation = useMutation({
    mutationFn: (droppedId: string) =>
      ShowsService.adminUnlinkShowFromCanonical({
        showId,
        canonicalShowId: droppedId,
      }),
    onSuccess: () => {
      showSuccessToast("Show unlinked from canonical show")
      rereadShow()
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  const linkedIds = new Set(canonicalShowIds)
  // A listing short enough to be sent whole comes back unfiltered and unpaged,
  // so the name is matched here as well as asked for above, and only then cut
  // down to what the box holds.
  const wanted = search.trim().toLowerCase()
  const offered = (results?.data ?? [])
    .filter(
      (show) =>
        !linkedIds.has(show.id) &&
        (show.name ?? "").toLowerCase().includes(wanted),
    )
    .slice(0, SEARCH_RESULT_COUNT)

  return (
    <div className="space-y-2">
      <Label htmlFor="canonical-show-search">Canonical Shows</Label>
      {canonicalShowIds.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Linked to no canonical show.
        </p>
      ) : (
        <div className="rounded-lg border">
          {canonicalShowIds.map((canonicalShowId) => {
            const show = linked.find((each) => each.id === canonicalShowId)
            return (
              <div
                key={canonicalShowId}
                className="flex items-center gap-3 border-b px-3 py-2 text-sm last:border-b-0"
              >
                {show ? (
                  <CanonicalShowName show={show} />
                ) : (
                  <span className="flex-1 text-muted-foreground">
                    Reading the linked title…
                  </span>
                )}
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="shrink-0"
                  title="Unlink from this canonical show"
                  disabled={unlinkMutation.isPending}
                  onClick={() => unlinkMutation.mutate(canonicalShowId)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            )
          })}
        </div>
      )}
      <Input
        id="canonical-show-search"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder="Search canonical shows by name"
      />
      {search.trim().length > SEARCH_MINIMUM_LENGTH ? (
        <div className="max-h-64 overflow-y-auto rounded-lg border">
          {offered.length === 0 ? (
            <p className="p-3 text-sm text-muted-foreground">
              {isFetching ? "Searching…" : "No canonical show under that name."}
            </p>
          ) : (
            offered.map((show) => (
              <div
                key={show.id}
                className="flex items-center gap-3 border-b px-3 py-2 text-sm last:border-b-0"
              >
                <CanonicalShowName show={show} />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="shrink-0"
                  disabled={linkMutation.isPending}
                  onClick={() => linkMutation.mutate(show.id)}
                >
                  Link
                </Button>
              </div>
            ))
          )}
        </div>
      ) : null}
    </div>
  )
}
