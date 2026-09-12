// TODO: Validate
import type { TitleBrowseOutput } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"

// TODO: Validate
export function TitleGrid({ titles }: { titles: TitleBrowseOutput[] }) {
  return (
    <div className="grid items-start justify-start gap-3 px-[4%] grid-cols-[repeat(auto-fill,minmax(min(100%,220px),220px))]">
      {titles.map((title) => {
        const artwork = title.thumbnail_url ?? title.image_url
        const name = title.name ?? ""

        return (
          <Card key={title.id} className="gap-0 overflow-hidden py-0">
            <div className="aspect-video w-full bg-muted">
              <img
                referrerPolicy="no-referrer"
                loading="lazy"
                decoding="async"
                src={artwork ?? "/no-image.svg"}
                alt={name}
                className="size-full object-cover"
              />
            </div>
            <div className="flex flex-col gap-2 p-3">
              <span className="wrap-break-word text-sm">
                <span className="font-bold">{name}</span>
                {title.year ? ` (${title.year})` : ""}
              </span>
              {title.media_type ? (
                <div>
                  <Badge variant="secondary">{title.media_type}</Badge>
                </div>
              ) : null}
            </div>
          </Card>
        )
      })}
    </div>
  )
}
