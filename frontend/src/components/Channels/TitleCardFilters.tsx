// TODO: Validate
import { ChevronDown, X } from "lucide-react"
import { useState } from "react"
import type { VideoStoreFacetsOutput } from "@/client"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import { Input } from "@/components/ui/input"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"

export type TitleCardFilters = {
  query?: string
  yearFrom?: number
  yearTo?: number
  tmdbScoreFrom?: number
  tmdbScoreTo?: number
  tmdbPopularityFrom?: number
  tmdbPopularityTo?: number
  imdbScoreFrom?: number
  imdbScoreTo?: number
  imdbPopularityFrom?: number
  imdbPopularityTo?: number
  mediaTypes?: string[]
  originalLanguages?: string[]
  spokenLanguages?: string[]
  genres?: string[]
}

type RangeKey =
  | "yearFrom"
  | "yearTo"
  | "tmdbScoreFrom"
  | "tmdbScoreTo"
  | "tmdbPopularityFrom"
  | "tmdbPopularityTo"
  | "imdbScoreFrom"
  | "imdbScoreTo"
  | "imdbPopularityFrom"
  | "imdbPopularityTo"

type ListKey = "mediaTypes" | "originalLanguages" | "spokenLanguages" | "genres"

// TODO: Validate
const readNumber = (value: unknown) =>
  typeof value === "number" && Number.isFinite(value) ? value : undefined

// TODO: Validate
const readList = (value: unknown) => {
  if (!Array.isArray(value)) return undefined
  const entries = value.filter(
    (entry): entry is string => typeof entry === "string",
  )
  return entries.length > 0 ? entries : undefined
}

// TODO: Validate
export const readTitleCardFilters = (
  search: Record<string, unknown>,
): TitleCardFilters => ({
  query:
    typeof search.query === "string" && search.query ? search.query : undefined,
  yearFrom: readNumber(search.yearFrom),
  yearTo: readNumber(search.yearTo),
  tmdbScoreFrom: readNumber(search.tmdbScoreFrom),
  tmdbScoreTo: readNumber(search.tmdbScoreTo),
  tmdbPopularityFrom: readNumber(search.tmdbPopularityFrom),
  tmdbPopularityTo: readNumber(search.tmdbPopularityTo),
  imdbScoreFrom: readNumber(search.imdbScoreFrom),
  imdbScoreTo: readNumber(search.imdbScoreTo),
  imdbPopularityFrom: readNumber(search.imdbPopularityFrom),
  imdbPopularityTo: readNumber(search.imdbPopularityTo),
  mediaTypes: readList(search.mediaTypes),
  originalLanguages: readList(search.originalLanguages),
  spokenLanguages: readList(search.spokenLanguages),
  genres: readList(search.genres),
})

// TODO: Validate
export const pickTitleCardFilters = (
  search: TitleCardFilters,
): TitleCardFilters => ({
  query: search.query,
  yearFrom: search.yearFrom,
  yearTo: search.yearTo,
  tmdbScoreFrom: search.tmdbScoreFrom,
  tmdbScoreTo: search.tmdbScoreTo,
  tmdbPopularityFrom: search.tmdbPopularityFrom,
  tmdbPopularityTo: search.tmdbPopularityTo,
  imdbScoreFrom: search.imdbScoreFrom,
  imdbScoreTo: search.imdbScoreTo,
  imdbPopularityFrom: search.imdbPopularityFrom,
  imdbPopularityTo: search.imdbPopularityTo,
  mediaTypes: search.mediaTypes,
  originalLanguages: search.originalLanguages,
  spokenLanguages: search.spokenLanguages,
  genres: search.genres,
})

// TODO: Validate
const hasAnyFilter = (filters: TitleCardFilters) =>
  Object.values(filters).some((value) => value !== undefined)

// TODO: Validate
const OptionsFilter = ({
  label,
  options,
  selected,
  onChange,
}: {
  label: string
  options: Array<{ value: string; label: string; count: number }>
  selected: string[] | undefined
  onChange: (selected: string[] | undefined) => void
}) => {
  const chosen = selected ?? []
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          type="button"
          size="sm"
          variant={chosen.length > 0 ? "secondary" : "outline"}
          className="h-9 gap-1"
        >
          {label}
          {chosen.length > 0 && ` · ${chosen.length}`}
          <ChevronDown className="size-3.5 opacity-60" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-72 p-0">
        <Command>
          <CommandInput placeholder={`Filter ${label.toLowerCase()}...`} />
          <CommandList>
            <CommandEmpty>No matches.</CommandEmpty>
            <CommandGroup>
              {options.map((option) => (
                <CommandItem
                  key={option.value}
                  value={`${option.label} ${option.value}`}
                  onSelect={() => {
                    const next = chosen.includes(option.value)
                      ? chosen.filter((entry) => entry !== option.value)
                      : [...chosen, option.value]
                    onChange(next.length > 0 ? next : undefined)
                  }}
                >
                  <Checkbox
                    checked={chosen.includes(option.value)}
                    className="pointer-events-none"
                  />
                  <span className="flex-1 truncate">{option.label}</span>
                  <span className="text-xs tabular-nums text-muted-foreground">
                    {option.count.toLocaleString()}
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
        {chosen.length > 0 && (
          <div className="border-t p-1">
            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="w-full"
              onClick={() => onChange(undefined)}
            >
              Clear
            </Button>
          </div>
        )}
      </PopoverContent>
    </Popover>
  )
}

// TODO: Validate
const RangeFilter = ({
  label,
  rows,
  filters,
  onChange,
}: {
  label: string
  rows: Array<{
    label: string
    from: RangeKey
    to: RangeKey
    step: number
    hint?: string
  }>
  filters: TitleCardFilters
  onChange: (changes: Partial<TitleCardFilters>) => void
}) => {
  const [draft, setDraft] = useState<Partial<Record<RangeKey, string>>>({})
  const keys = rows.flatMap((row) => [row.from, row.to])
  const activeCount = keys.filter((key) => filters[key] !== undefined).length

  // TODO: Validate
  const commit = () => {
    const changes: Partial<TitleCardFilters> = {}
    for (const key of keys) {
      const typed = draft[key]
      if (typed === undefined) continue
      const parsed = Number(typed)
      changes[key] =
        typed.trim() === "" || Number.isNaN(parsed) ? undefined : parsed
    }
    setDraft({})
    if (Object.keys(changes).length > 0) onChange(changes)
  }

  return (
    <Popover
      onOpenChange={(open) => {
        if (!open) commit()
      }}
    >
      <PopoverTrigger asChild>
        <Button
          type="button"
          size="sm"
          variant={activeCount > 0 ? "secondary" : "outline"}
          className="h-9 gap-1"
        >
          {label}
          {activeCount > 0 && ` · ${activeCount}`}
          <ChevronDown className="size-3.5 opacity-60" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-80">
        <form
          className="flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault()
            commit()
          }}
        >
          {rows.map((row) => (
            <div key={row.from} className="flex flex-col gap-1.5">
              <span className="text-xs font-medium text-muted-foreground">
                {row.label}
              </span>
              <div className="flex items-center gap-2">
                {[row.from, row.to].map((key, index) => (
                  <Input
                    key={key}
                    type="number"
                    step={row.step}
                    placeholder={index === 0 ? "From" : "To"}
                    value={draft[key] ?? filters[key]?.toString() ?? ""}
                    onChange={(event) =>
                      setDraft({ ...draft, [key]: event.target.value })
                    }
                    className="h-8"
                  />
                ))}
              </div>
              {row.hint && (
                <span className="text-[11px] text-muted-foreground">
                  {row.hint}
                </span>
              )}
            </div>
          ))}
          <div className="flex justify-end gap-2">
            {activeCount > 0 && (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => {
                  setDraft({})
                  onChange(
                    Object.fromEntries(keys.map((key) => [key, undefined])),
                  )
                }}
              >
                Clear
              </Button>
            )}
            <Button type="submit" size="sm">
              Apply
            </Button>
          </div>
        </form>
      </PopoverContent>
    </Popover>
  )
}

// TODO: Validate
export function TitleCardFilterBar({
  filters,
  facets,
  onChange,
}: {
  filters: TitleCardFilters
  facets: VideoStoreFacetsOutput | undefined
  onChange: (filters: TitleCardFilters) => void
}) {
  const [typedQuery, setTypedQuery] = useState(filters.query ?? "")

  // TODO: Validate
  const change = (changes: Partial<TitleCardFilters>) =>
    onChange({ ...filters, ...changes })

  // TODO: Validate
  const listFilter = (
    key: ListKey,
    label: string,
    options: Array<{ value: string; label: string; count: number }>,
  ) => (
    <OptionsFilter
      label={label}
      options={options}
      selected={filters[key]}
      onChange={(selected) => change({ [key]: selected })}
    />
  )

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-card p-2">
      <form
        onSubmit={(event) => {
          event.preventDefault()
          change({ query: typedQuery || undefined })
        }}
      >
        <Input
          type="search"
          value={typedQuery}
          onChange={(event) => setTypedQuery(event.target.value)}
          placeholder="Search titles"
          className="h-9 w-56"
        />
      </form>
      {listFilter(
        "mediaTypes",
        "Media type",
        (facets?.media_types ?? []).map((option) => ({
          value: option.name,
          label: option.name,
          count: option.title_count,
        })),
      )}
      {listFilter(
        "genres",
        "Genres",
        (facets?.genres ?? []).map((option) => ({
          value: option.name,
          label: option.name,
          count: option.title_count,
        })),
      )}
      {listFilter(
        "originalLanguages",
        "Original language",
        (facets?.original_languages ?? []).map((option) => ({
          value: option.code,
          label: option.name ?? option.code,
          count: option.title_count,
        })),
      )}
      {listFilter(
        "spokenLanguages",
        "Spoken language",
        (facets?.spoken_languages ?? []).map((option) => ({
          value: option.code,
          label: option.name ?? option.code,
          count: option.title_count,
        })),
      )}
      <RangeFilter
        label="Year"
        rows={[{ label: "Year", from: "yearFrom", to: "yearTo", step: 1 }]}
        filters={filters}
        onChange={change}
      />
      <RangeFilter
        label="Score"
        rows={[
          {
            label: "TMDB score",
            from: "tmdbScoreFrom",
            to: "tmdbScoreTo",
            step: 0.1,
          },
          {
            label: "IMDb score",
            from: "imdbScoreFrom",
            to: "imdbScoreTo",
            step: 0.1,
          },
        ]}
        filters={filters}
        onChange={change}
      />
      <RangeFilter
        label="Popularity"
        rows={[
          {
            label: "TMDB popularity",
            from: "tmdbPopularityFrom",
            to: "tmdbPopularityTo",
            step: 0.1,
          },
          {
            label: "IMDb popularity rank",
            from: "imdbPopularityFrom",
            to: "imdbPopularityTo",
            step: 1,
            hint: "A rank, so 1 is the most popular.",
          },
        ]}
        filters={filters}
        onChange={change}
      />
      {hasAnyFilter(filters) && (
        <Button
          type="button"
          size="sm"
          variant="ghost"
          className="h-9 gap-1"
          onClick={() => {
            setTypedQuery("")
            onChange({})
          }}
        >
          <X className="size-3.5" />
          Clear all
        </Button>
      )}
    </div>
  )
}
