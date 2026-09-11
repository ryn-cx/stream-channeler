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
  TitlesService,
  type TmdbTitleOutput,
  TmdbTitlesService,
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

interface TmdbTitleFieldProps {
  titleId: string
  tmdbTitleIds: string[]
  /** Only asked for while the form is open, since each is a query of its own. */
  enabled: boolean
}

// TODO: Validate
function TmdbTitleName({ title }: { title: TmdbTitleOutput }) {
  return (
    <span className="flex-1 whitespace-normal wrap-break-word">
      {title.tmdb_url ? (
        <a
          href={title.tmdb_url}
          target="_blank"
          rel="noopener noreferrer"
          className="hover:underline"
        >
          {title.name ?? "Unnamed"}
        </a>
      ) : (
        (title.name ?? "Unnamed")
      )}
      {title.year ? (
        <span className="text-muted-foreground"> ({title.year})</span>
      ) : null}
      <span className="block text-xs text-muted-foreground">{title.key}</span>
    </span>
  )
}

// TODO: Validate
/**
 * Which tmdb titles this row stands for, and the choosing of another.
 *
 * A row is linked to its titles by the import that read it,
 * which is a guess made off the name and the year and is wrong often enough to
 * be worth settling by hand. Choosing here adds to what the row already stands
 * for rather than replacing it, since one page holding two titles - a channel
 * whose uploads are two series, a sequel sold as another season - is a thing
 * websites do. Taking one off is the X beside it.
 *
 * The links are written as soon as they are chosen rather than with the rest of
 * the form: they are rows of their own, and what they drag along - every episode
 * read again against the titles left - is not something the title's own columns
 * do.
 */
export function TmdbTitleField({
  titleId,
  tmdbTitleIds,
  enabled,
}: TmdbTitleFieldProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const [search, setSearch] = useState("")
  const [urlDraft, setUrlDraft] = useState("")

  const linkedQueries = useQueries({
    queries: tmdbTitleIds.map((tmdbTitleId) => ({
      queryKey: ["tmdb-title", tmdbTitleId],
      queryFn: () => TmdbTitlesService.getTmdbTitleById({ tmdbTitleId }),
      enabled,
    })),
  })
  const linked = linkedQueries
    .map((query) => query.data)
    .filter((title) => title !== undefined)

  const { data: results, isFetching } = useQuery({
    queryKey: ["tmdb-titles", "search", search],
    queryFn: () =>
      TmdbTitlesService.getTmdbTitles({
        filterOptions: JSON.stringify([{ id: "name", value: search }]),
        limit: SEARCH_RESULT_COUNT,
      }),
    enabled: enabled && search.trim().length > SEARCH_MINIMUM_LENGTH,
  })

  // TODO: Validate
  const rereadTitle = () => {
    queryClient.invalidateQueries({ queryKey: ["titles"] })
    queryClient.invalidateQueries({ queryKey: ["title-information", titleId] })
    queryClient.invalidateQueries({ queryKey: ["tmdb-title"] })
  }

  const linkMutation = useMutation({
    mutationFn: (chosenId: string) =>
      TitlesService.adminLinkTitleToTmdb({
        titleId,
        tmdbTitleId: chosenId,
      }),
    onSuccess: () => {
      showSuccessToast("Title linked to tmdb title")
      setSearch("")
      rereadTitle()
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  const urlMutation = useMutation({
    mutationFn: () =>
      TitlesService.adminLinkTitleByTmdbUrl({
        titleId,
        requestBody: { url: urlDraft },
      }),
    onSuccess: () => {
      showSuccessToast("Title linked to tmdb title")
      setUrlDraft("")
      rereadTitle()
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  const unlinkMutation = useMutation({
    mutationFn: (droppedId: string) =>
      TitlesService.adminUnlinkTitleFromTmdb({
        titleId,
        tmdbTitleId: droppedId,
      }),
    onSuccess: () => {
      showSuccessToast("Title unlinked from tmdb title")
      rereadTitle()
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  const linkedIds = new Set(tmdbTitleIds)
  // A listing short enough to be sent whole comes back unfiltered and unpaged,
  // so the name is matched here as well as asked for above, and only then cut
  // down to what the box holds.
  const wanted = search.trim().toLowerCase()
  const offered = (results?.data ?? [])
    .filter(
      (title) =>
        !linkedIds.has(title.id) &&
        (title.name ?? "").toLowerCase().includes(wanted),
    )
    .slice(0, SEARCH_RESULT_COUNT)

  return (
    <div className="space-y-2">
      <Label htmlFor="tmdb-title-search">TMDB Titles</Label>
      {tmdbTitleIds.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Linked to no tmdb title.
        </p>
      ) : (
        <div className="rounded-lg border">
          {tmdbTitleIds.map((tmdbTitleId) => {
            const title = linked.find((each) => each.id === tmdbTitleId)
            return (
              <div
                key={tmdbTitleId}
                className="flex items-center gap-3 border-b px-3 py-2 text-sm last:border-b-0"
              >
                {title ? (
                  <TmdbTitleName title={title} />
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
                  title="Unlink from this tmdb title"
                  disabled={unlinkMutation.isPending}
                  onClick={() => unlinkMutation.mutate(tmdbTitleId)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            )
          })}
        </div>
      )}
      <Input
        id="tmdb-title-search"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder="Search tmdb titles by name"
      />
      {search.trim().length > SEARCH_MINIMUM_LENGTH ? (
        <div className="max-h-64 overflow-y-auto rounded-lg border">
          {offered.length === 0 ? (
            <p className="p-3 text-sm text-muted-foreground">
              {isFetching ? "Searching…" : "No tmdb title under that name."}
            </p>
          ) : (
            offered.map((title) => (
              <div
                key={title.id}
                className="flex items-center gap-3 border-b px-3 py-2 text-sm last:border-b-0"
              >
                <TmdbTitleName title={title} />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="shrink-0"
                  disabled={linkMutation.isPending}
                  onClick={() => linkMutation.mutate(title.id)}
                >
                  Link
                </Button>
              </div>
            ))
          )}
        </div>
      ) : null}
      <div className="flex flex-wrap items-center gap-2">
        <Input
          value={urlDraft}
          onChange={(event) => setUrlDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key !== "Enter") return
            event.preventDefault()
            if (urlDraft.trim().length > 0) urlMutation.mutate()
          }}
          placeholder="themoviedb.org address of a film or series"
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
