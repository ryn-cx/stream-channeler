// TODO: Validate
import { useQuery } from "@tanstack/react-query"

import { ShowsService } from "@/client"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

/** The plugin whose rows carry an episode order. */
export const TMDB_EPISODE_ORDER_PLUGIN = "TMDB"

/** What a title read in TMDB's own order stores, which is nothing at all. */
export const TMDB_OWN_ORDER = "__own__"

// TODO: Validate
/** Read the episode order out of what a TMDB `Show` keeps in `extra`. */
export function episodeGroupIdOf(
  extra: Record<string, unknown> | null | undefined,
): string {
  const groupId = extra?.tmdb_episode_group_id
  // `extra` is shared with whatever else a plugin keeps there, so anything that
  // is not an order reads as no order chosen rather than as a fault.
  return typeof groupId === "string" && groupId ? groupId : TMDB_OWN_ORDER
}

// TODO: Validate
/**
 * Set the episode order on what a `Show` already keeps in `extra`.
 *
 * Written onto whatever else is stored rather than over it, since `extra` is one
 * column holding everything a plugin says about a title and the order is one
 * key of it. Put back to TMDB's own order the key goes rather than being stored
 * as empty, so a title never moved off it and one moved back read alike.
 */
export function withEpisodeGroupId(
  extra: Record<string, unknown>,
  groupId: string,
): Record<string, unknown> {
  const { tmdb_episode_group_id: _removed, ...rest } = extra
  if (groupId === TMDB_OWN_ORDER) return rest
  return { ...rest, tmdb_episode_group_id: groupId }
}

interface TmdbEpisodeOrderFieldProps {
  showId: string
  value: string
  onChange: (groupId: string) => void
  /** Only asked for while the form is open, since it reads a downloaded file. */
  enabled: boolean
}

// TODO: Validate
/**
 * Which of TMDB's episode orders the title is read in.
 *
 * TMDB numbers a series the way it first aired and keeps the other orders - the
 * DVD order, the story order, a streaming service's own - beside it. A title
 * whose website follows one of those lines up against nothing until the same
 * order is read here, so one can be chosen and the title's seasons are rebuilt
 * from it on the next import.
 */
export function TmdbEpisodeOrderField({
  showId,
  value,
  onChange,
  enabled,
}: TmdbEpisodeOrderFieldProps) {
  const { data: groups, isLoading } = useQuery({
    queryKey: ["show-tmdb-episode-groups", showId],
    queryFn: () => ShowsService.getShowTmdbEpisodeGroups({ showId }),
    enabled,
  })

  const options = groups ?? []

  return (
    <div className="space-y-2">
      <Label htmlFor="tmdb-episode-order">Episode order</Label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger id="tmdb-episode-order">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={TMDB_OWN_ORDER}>
            TMDB's own order (aired)
          </SelectItem>
          {options.map((group) => (
            <SelectItem key={group.id} value={group.id}>
              {group.name} — {group.group_count} seasons, {group.episode_count}{" "}
              episodes
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <p className="text-xs text-muted-foreground">
        {isLoading
          ? "Reading the orders TMDB holds…"
          : options.length === 0
            ? "TMDB holds no other order for this title."
            : "Choosing an order replaces this title's seasons with it on the next import."}
      </p>
    </div>
  )
}
