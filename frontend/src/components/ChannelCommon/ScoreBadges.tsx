// TODO: Validate
import { Favicon } from "@/components/Common/Favicon"
import { Badge } from "@/components/ui/badge"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"

export interface ScoredTitle {
  tmdb_score?: number | null
  tmdb_popularity?: number | null
  imdb_score?: number | null
  imdb_popularity?: number | null
}

// TODO: Validate
export function ScoreBadges({ title }: { title: ScoredTitle }) {
  const badges = [
    {
      key: "tmdb-score",
      iconUrl: "/tmdb.svg",
      iconLabel: "TMDB",
      value: title.tmdb_score,
      description: "TMDB Score",
      text: `Score ${title.tmdb_score?.toFixed(1)}`,
    },
    {
      key: "tmdb-popularity",
      iconUrl: "/tmdb.svg",
      iconLabel: "TMDB",
      value: title.tmdb_popularity,
      description: "TMDB Popularity",
      text: `Popularity ${title.tmdb_popularity?.toFixed(1)}`,
    },
    {
      key: "imdb-score",
      iconUrl: "/imdb.svg",
      iconLabel: "IMDb",
      value: title.imdb_score,
      description: "IMDb Score",
      text: `Score ${title.imdb_score?.toFixed(1)}`,
    },
    {
      key: "imdb-popularity",
      iconUrl: "/imdb.svg",
      iconLabel: "IMDb",
      value: title.imdb_popularity,
      description: "IMDb Popularity Rank",
      text: `Popularity #${title.imdb_popularity?.toLocaleString()}`,
    },
  ]
  return badges
    .filter((badge) => badge.value != null)
    .map((badge) => (
      <Tooltip key={badge.key}>
        <TooltipTrigger asChild>
          <Badge variant="secondary">
            <Favicon
              src={badge.iconUrl}
              label={badge.iconLabel}
              className="size-3.5"
              tooltip={false}
            />
            {badge.text}
          </Badge>
        </TooltipTrigger>
        <TooltipContent>{badge.description}</TooltipContent>
      </Tooltip>
    ))
}
