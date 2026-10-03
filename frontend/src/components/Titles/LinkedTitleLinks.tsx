// TODO: Validate
import { useQuery } from "@tanstack/react-query"

import { TitlesService } from "@/client"
import { ResultCard } from "@/components/Channels/ChannelDetail/Search"
import { Label } from "@/components/ui/label"
import { useOpenMedia } from "@/hooks/useOpenMedia"

interface LinkedTitleLinksProps {
  titleId: string
  enabled: boolean
}

// TODO: Validate
export function LinkedTitleLinks({ titleId, enabled }: LinkedTitleLinksProps) {
  const openMedia = useOpenMedia()
  const { data: titles, isLoading } = useQuery({
    queryKey: ["titles", titleId, "linked"],
    queryFn: () => TitlesService.getLinkedTitles({ titleId }),
    enabled,
  })

  if (isLoading) {
    return (
      <p className="text-sm text-muted-foreground">
        Reading the linked titles…
      </p>
    )
  }

  return (
    <div className="space-y-2">
      <Label>Linked Titles</Label>
      {!titles || titles.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No title is linked to this title.
        </p>
      ) : (
        <div className="flex flex-wrap gap-3">
          {titles.map((linked) => (
            <ResultCard
              key={linked.id}
              imageUrl={
                linked.poster_thumbnail_url ??
                linked.poster_url ??
                linked.thumbnail_url ??
                linked.image_url
              }
              title={
                linked.year
                  ? `${linked.name ?? "Unnamed"} (${linked.year})`
                  : (linked.name ?? "Unnamed")
              }
              subtitle={
                <>
                  <span>{linked.source_key}</span>
                  {linked.media_type ? (
                    <span className="block">{linked.media_type}</span>
                  ) : null}
                </>
              }
              onClick={() => openMedia({ kind: "title", titleId: linked.id })}
            />
          ))}
        </div>
      )}
    </div>
  )
}
