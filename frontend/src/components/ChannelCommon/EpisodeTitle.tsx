// TODO: Validate

// TODO: Validate
export function EpisodeTitle({
  name,
  episodeNumber,
}: {
  name: string | null | undefined
  episodeNumber: number | null | undefined
}) {
  return (
    <>
      {episodeNumber == null ? null : (
        <span className="text-muted-foreground">{episodeNumber}. </span>
      )}
      {name || "Untitled"}
    </>
  )
}
