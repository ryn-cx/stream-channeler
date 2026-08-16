// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
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
  canonicalShowId: string | null | undefined
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
 * Which canonical show this row stands for, and the choosing of another.
 *
 * A row is linked to the title it is a copy of by the import that read it, which
 * is a guess made off the name and the year and is wrong often enough to be
 * worth settling by hand. Choosing here takes the row off whatever it was linked
 * to, so a row stands for the one title chosen rather than for both.
 *
 * The link is written as soon as it is chosen rather than with the rest of the
 * form: it is a row of its own, and what it drags along - every episode read
 * again against the title chosen - is not something the show's own columns do.
 */
export function CanonicalShowField({
  showId,
  canonicalShowId,
  enabled,
}: CanonicalShowFieldProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const [search, setSearch] = useState("")

  const { data: linked } = useQuery({
    queryKey: ["canonical-show", canonicalShowId],
    queryFn: () =>
      CanonicalShowsService.getCanonicalShowById({
        canonicalShowId: canonicalShowId as string,
      }),
    enabled: enabled && Boolean(canonicalShowId),
  })

  const { data: results, isFetching } = useQuery({
    queryKey: ["canonical-shows", "search", search],
    queryFn: () =>
      CanonicalShowsService.getCanonicalShows({
        filterOptions: JSON.stringify([{ id: "name", value: search }]),
        limit: SEARCH_RESULT_COUNT,
      }),
    enabled: enabled && search.trim().length > SEARCH_MINIMUM_LENGTH,
  })

  const linkMutation = useMutation({
    mutationFn: (chosenId: string) =>
      ShowsService.adminLinkShowToCanonical({
        showId,
        canonicalShowId: chosenId,
      }),
    onSuccess: () => {
      showSuccessToast("Show linked to canonical show")
      setSearch("")
      queryClient.invalidateQueries({ queryKey: ["shows"] })
      queryClient.invalidateQueries({ queryKey: ["show-information", showId] })
      queryClient.invalidateQueries({ queryKey: ["canonical-show"] })
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  const offered = (results?.data ?? []).filter((show) => show.id !== linked?.id)

  return (
    <div className="space-y-2">
      <Label htmlFor="canonical-show-search">Canonical Show</Label>
      <p className="text-sm">
        {canonicalShowId ? (
          linked ? (
            <CanonicalShowName show={linked} />
          ) : (
            "Reading the linked title…"
          )
        ) : (
          <span className="text-muted-foreground">
            Linked to no canonical show.
          </span>
        )}
      </p>
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
