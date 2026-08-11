// TODO: Validate
import { useEffect, useState } from "react"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

export type TmdbMediaType = "tv" | "movie"

const TMDB_IDENTIFIER_PATTERN = /^TMDB (tv|movie) (\d+)$/

// TODO: Validate
export const parseTmdbIdentifier = (identifier: string) => {
  const match = TMDB_IDENTIFIER_PATTERN.exec(identifier)
  if (!match) {
    return null
  }
  return { mediaType: match[1] as TmdbMediaType, tmdbId: match[2] }
}

// TODO: Validate
export const buildTmdbIdentifier = (mediaType: TmdbMediaType, tmdbId: string) =>
  `TMDB ${mediaType} ${tmdbId}`

interface TmdbIdentifierFieldProps {
  identifier: string
  onChange: (identifier: string) => void
}

// TODO: Validate
export const TmdbIdentifierField = ({
  identifier,
  onChange,
}: TmdbIdentifierFieldProps) => {
  const parsed = parseTmdbIdentifier(identifier)
  const [mediaType, setMediaType] = useState<TmdbMediaType>(
    parsed?.mediaType ?? "tv",
  )
  const [tmdbId, setTmdbId] = useState(parsed?.tmdbId ?? "")

  useEffect(() => {
    const current = parseTmdbIdentifier(identifier)
    if (current) {
      setMediaType(current.mediaType)
      setTmdbId(current.tmdbId)
    } else {
      setTmdbId("")
    }
  }, [identifier])

  // TODO: Validate
  const apply = (nextMediaType: TmdbMediaType, nextTmdbId: string) => {
    if (nextTmdbId) {
      onChange(buildTmdbIdentifier(nextMediaType, nextTmdbId))
    }
  }

  return (
    <div className="grid gap-2">
      <Label>TMDB Identifier</Label>
      <div className="flex items-center gap-2">
        <Select
          value={mediaType}
          onValueChange={(value) => {
            const nextMediaType = value as TmdbMediaType
            setMediaType(nextMediaType)
            apply(nextMediaType, tmdbId)
          }}
        >
          <SelectTrigger className="w-28">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="tv">TV</SelectItem>
            <SelectItem value="movie">Movie</SelectItem>
          </SelectContent>
        </Select>
        <Input
          type="number"
          placeholder="12345"
          value={tmdbId}
          onChange={(event) => {
            setTmdbId(event.target.value)
            apply(mediaType, event.target.value)
          }}
        />
      </div>
    </div>
  )
}
