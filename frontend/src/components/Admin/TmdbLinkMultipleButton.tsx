// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { CircleSlash, Link } from "lucide-react"

import { EpisodesService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import type { TmdbMatchRow } from "./tmdbMatchColumns"
import {
  SETTLE_TMDB_MATCH_MUTATION_KEY,
  type SettleTmdbMatchVariables,
  useRereadTmdbMatches,
} from "./tmdbMatchesQuery"
import {
  MATCH_KINDS,
  type MatchField,
  useTmdbMatchSelection,
} from "./tmdbMatchSelection"

// TODO: Validate
// TODO: Validate
function firstMatch(row: TmdbMatchRow, field: MatchField) {
  const found = row[field]
  return Array.isArray(found) ? found[0] : found
}

// TODO: Validate
export function TmdbLinkMultipleButton() {
  const selection = useTmdbMatchSelection()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const reread = useRereadTmdbMatches()

  const linkMutation = useMutation({
    mutationKey: SETTLE_TMDB_MATCH_MUTATION_KEY,
    mutationFn: async ({
      rows,
      field,
    }: SettleTmdbMatchVariables & {
      rows: TmdbMatchRow[]
      field: MatchField
    }) => {
      const linkable = rows.flatMap((row) => {
        const match = firstMatch(row, field)
        return match
          ? [
              {
                episode_id: row.episode.id,
                canonical_episode_id: match.episode.id,
              },
            ]
          : []
      })
      await EpisodesService.adminLinkEpisodesToTmdb({ requestBody: linkable })
      return {
        linked: linkable.length,
        skipped: rows.length - linkable.length,
      }
    },
    onSuccess: ({ linked, skipped }) => {
      selection?.clear()
      showSuccessToast(
        skipped
          ? `Linked ${linked}, left ${skipped} with no match of that kind`
          : `Linked ${linked}`,
      )
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
    onSettled: reread,
  })

  const absentMutation = useMutation({
    mutationKey: SETTLE_TMDB_MATCH_MUTATION_KEY,
    mutationFn: async ({ episodeIds }: SettleTmdbMatchVariables) => {
      await EpisodesService.adminMarkEpisodesAbsentFromTmdb({
        requestBody: episodeIds,
      })
      return episodeIds.length
    },
    onSuccess: (marked) => {
      selection?.clear()
      showSuccessToast(`Marked ${marked} as not on TMDB`)
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
    onSettled: reread,
  })

  const count = selection?.selectedIds.length ?? 0
  const isPending = linkMutation.isPending || absentMutation.isPending
  if (!selection) return null

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          disabled={count === 0 || isPending}
          title="Settle every selected row the same way"
        >
          <Link />
          Link Multiple{count ? ` (${count})` : ""}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>Link {count} by</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {MATCH_KINDS.map(({ kind, label, field }) => {
          const offered = selection.selectedRows.filter((row) =>
            firstMatch(row, field),
          ).length
          return (
            <DropdownMenuItem
              key={kind}
              disabled={offered === 0}
              onSelect={() =>
                linkMutation.mutate({
                  episodeIds: selection.selectedIds,
                  rows: selection.selectedRows,
                  field,
                })
              }
            >
              {label}
              <span className="ml-auto pl-4 text-xs tabular-nums text-muted-foreground">
                {offered}/{count}
              </span>
            </DropdownMenuItem>
          )
        })}
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onSelect={() =>
            absentMutation.mutate({ episodeIds: selection.selectedIds })
          }
        >
          <CircleSlash className="h-4 w-4" />
          Not on TMDB
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => selection.clear()}>
          Clear selection
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
