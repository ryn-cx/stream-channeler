// TODO: Validate
import type { DuplicatedLinkEpisodeOutput } from "@/client"
import EditEpisode from "@/components/Episodes/Edit"

interface DuplicatedCanonicalEpisodeLinksProps {
  episodes: DuplicatedLinkEpisodeOutput[]
}

// TODO: Validate
function numbering(
  seasonNumber: number | null | undefined,
  episodeNumber: number | null | undefined,
): string {
  return `S${seasonNumber ?? "?"}E${episodeNumber ?? "?"}`
}

// TODO: Validate
export function DuplicatedCanonicalEpisodeLinks({
  episodes,
}: DuplicatedCanonicalEpisodeLinksProps) {
  return (
    <div className="flex min-w-64 flex-col gap-1 py-1">
      {episodes.map((episode) => (
        <div key={episode.id} className="flex items-center gap-2">
          <span className="shrink-0 font-mono text-muted-foreground text-xs">
            {numbering(episode.season_number, episode.episode_number)}
          </span>
          {episode.url ? (
            <a
              href={episode.url}
              target="_blank"
              rel="noreferrer"
              className="truncate text-sm hover:underline"
            >
              {episode.name ?? "Unnamed"}
            </a>
          ) : (
            <span className="truncate text-sm">
              {episode.name ?? "Unnamed"}
            </span>
          )}
          {episode.canonical_episode_validated_at ? (
            <span className="shrink-0 text-muted-foreground text-xs">
              Validated
            </span>
          ) : null}
          <div className="ml-auto shrink-0">
            <EditEpisode episode={episode} />
          </div>
        </div>
      ))}
    </div>
  )
}
