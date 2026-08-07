// TODO: Validate

/** Link to the episode's own page on themoviedb.org, when it has one. */
export function TmdbLink({
  url,
  className,
}: {
  url?: string | null
  className?: string
}) {
  if (!url) return null

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      aria-label="View on TMDB"
      title="View on TMDB"
      className={`z-20 rounded bg-background/90 px-1.5 py-0.5 text-[10px] font-semibold tracking-wide text-foreground shadow-md transition-colors hover:bg-background ${className ?? ""}`}
      onClick={(event) => event.stopPropagation()}
    >
      TMDB
    </a>
  )
}
