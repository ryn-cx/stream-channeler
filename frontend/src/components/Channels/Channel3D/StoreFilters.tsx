// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { ChevronDown, SlidersHorizontal, X } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { compareGenres, type StoreTitle } from "./caseTexture"
import { FORMATS, PALETTE, type StoreDesign } from "./StoreDesign"
import { fetchOriginalLanguages, fetchSpokenLanguages } from "./storeLanguages"

export type StoreFilters = {
  yearFrom: number
  yearTo: number
  unknownYear: boolean
  scoreSource: "tmdb" | "imdb"
  scoreFrom: number
  scoreTo: number
  unknownScore: boolean
  popularitySource: "tmdb" | "imdb"
  popularityFrom: number
  popularityTo: number
  unknownPopularity: boolean
  mediaTypes: string[]
  unknownMediaType: boolean
  originalLanguages: string[] | null
  unknownOriginalLanguage: boolean
  languages: string[] | null
  unknownLanguage: boolean
  genres: string[] | null
  unknownGenre: boolean
}

export const UNKNOWN_MEDIA_TYPE = "Unknown"

type StoreBounds = {
  yearFrom: number
  yearTo: number
  score: Record<"tmdb" | "imdb", { from: number; to: number }>
  popularity: Record<"tmdb" | "imdb", { from: number; to: number }>
  mediaTypes: string[]
  genres: string[]
  originalLanguages: string[]
  languages: string[]
  counts: Record<
    "mediaTypes" | "genres" | "originalLanguages" | "languages",
    Map<string, number>
  >
}

const boundsCache = new WeakMap<StoreTitle[], StoreBounds>()

// TODO: Validate
export const titleScore = (title: StoreTitle, source: "tmdb" | "imdb") =>
  source === "imdb" ? title.imdbScore : title.tmdbScore

// TODO: Validate
export const titlePopularity = (title: StoreTitle, source: "tmdb" | "imdb") =>
  source === "imdb" ? title.imdbPopularity : title.tmdbPopularity

// TODO: Validate
const valueRange = (
  titles: StoreTitle[],
  read: (title: StoreTitle) => number | null,
) => {
  let from = Number.POSITIVE_INFINITY
  let to = Number.NEGATIVE_INFINITY
  for (const title of titles) {
    const value = read(title)
    if (value === null) continue
    if (value < from) from = value
    if (value > to) to = value
  }
  return {
    from: Number.isFinite(from) ? Math.floor(from) : 0,
    to: Number.isFinite(to) ? Math.ceil(to) : 0,
  }
}

// TODO: Validate
export const storeBounds = (titles: StoreTitle[]): StoreBounds => {
  const cached = boundsCache.get(titles)
  if (cached) return cached

  let yearFrom = Number.POSITIVE_INFINITY
  let yearTo = Number.NEGATIVE_INFINITY
  const counts: StoreBounds["counts"] = {
    mediaTypes: new Map(),
    genres: new Map(),
    originalLanguages: new Map(),
    languages: new Map(),
  }
  // TODO: Validate
  const tally = (counted: Map<string, number>, values: Iterable<string>) => {
    for (const value of new Set(values)) {
      counted.set(value, (counted.get(value) ?? 0) + 1)
    }
  }
  // TODO: Validate
  const byCount = (counted: Map<string, number>) =>
    [...counted.keys()].sort(
      (left, right) => (counted.get(right) ?? 0) - (counted.get(left) ?? 0),
    )

  for (const title of titles) {
    if (title.year !== null) {
      if (title.year < yearFrom) yearFrom = title.year
      if (title.year > yearTo) yearTo = title.year
    }
    if (title.mediaType !== null) tally(counts.mediaTypes, [title.mediaType])
    tally(counts.genres, title.genres)
    if (title.originalLanguage !== null) {
      tally(counts.originalLanguages, [title.originalLanguage])
    }
    tally(counts.languages, title.languages)
  }

  const bounds: StoreBounds = {
    yearFrom: Number.isFinite(yearFrom) ? yearFrom : 0,
    yearTo: Number.isFinite(yearTo) ? yearTo : 0,
    score: {
      tmdb: valueRange(titles, (title) => title.tmdbScore),
      imdb: valueRange(titles, (title) => title.imdbScore),
    },
    popularity: {
      tmdb: valueRange(titles, (title) => title.tmdbPopularity),
      imdb: valueRange(titles, (title) => title.imdbPopularity),
    },
    mediaTypes: [...counts.mediaTypes.keys()].sort((left, right) =>
      left.localeCompare(right),
    ),
    genres: [...counts.genres.keys()].sort(compareGenres),
    originalLanguages: byCount(counts.originalLanguages),
    languages: byCount(counts.languages),
    counts,
  }
  boundsCache.set(titles, bounds)
  return bounds
}

// TODO: Validate
export const defaultFilters = (titles: StoreTitle[]): StoreFilters => {
  const bounds = storeBounds(titles)
  return {
    yearFrom: bounds.yearFrom,
    yearTo: bounds.yearTo,
    unknownYear: true,
    scoreSource: "tmdb",
    scoreFrom: bounds.score.tmdb.from,
    scoreTo: bounds.score.tmdb.to,
    unknownScore: true,
    popularitySource: "tmdb",
    popularityFrom: bounds.popularity.tmdb.from,
    popularityTo: bounds.popularity.tmdb.to,
    unknownPopularity: true,
    mediaTypes: bounds.mediaTypes,
    unknownMediaType: true,
    originalLanguages: null,
    unknownOriginalLanguage: true,
    languages: null,
    unknownLanguage: true,
    genres: null,
    unknownGenre: true,
  }
}

// TODO: Validate
export const applyFilters = (titles: StoreTitle[], filters: StoreFilters) => {
  const mediaTypes = new Set(filters.mediaTypes)
  const originalLanguages =
    filters.originalLanguages === null
      ? null
      : new Set(filters.originalLanguages)
  const languages =
    filters.languages === null ? null : new Set(filters.languages)
  const genres = filters.genres === null ? null : new Set(filters.genres)

  const shelved: StoreTitle[] = []
  for (const title of titles) {
    if (title.year === null) {
      if (!filters.unknownYear) continue
    } else if (title.year < filters.yearFrom || title.year > filters.yearTo) {
      continue
    }

    const score = titleScore(title, filters.scoreSource)
    if (score === null) {
      if (!filters.unknownScore) continue
    } else if (score < filters.scoreFrom || score > filters.scoreTo) {
      continue
    }

    const popularity = titlePopularity(title, filters.popularitySource)
    if (popularity === null) {
      if (!filters.unknownPopularity) continue
    } else if (
      popularity < filters.popularityFrom ||
      popularity > filters.popularityTo
    ) {
      continue
    }

    if (title.mediaType === null) {
      if (!filters.unknownMediaType) continue
    } else if (!mediaTypes.has(title.mediaType)) {
      continue
    }

    if (title.originalLanguage === null) {
      if (!filters.unknownOriginalLanguage) continue
    } else if (
      originalLanguages !== null &&
      !originalLanguages.has(title.originalLanguage)
    ) {
      continue
    }

    if (title.languages.length === 0) {
      if (!filters.unknownLanguage) continue
    } else if (
      languages !== null &&
      !title.languages.some((code) => languages.has(code))
    ) {
      continue
    }

    if (title.genres.length === 0) {
      if (!filters.unknownGenre) continue
    } else if (
      genres !== null &&
      !title.genres.some((genre) => genres.has(genre))
    ) {
      continue
    }

    shelved.push(title)
  }
  return shelved
}

// TODO: Validate
const NumberField = ({
  label,
  value,
  onChange,
}: {
  label: string
  value: number
  onChange: (value: number) => void
}) => {
  const [typed, setTyped] = useState<string | null>(null)

  return (
    <label className="flex flex-1 flex-col gap-1 text-[11px] uppercase tracking-wide text-white/45">
      {label}
      <input
        type="text"
        inputMode="decimal"
        value={typed ?? String(value)}
        onFocus={(event) => event.currentTarget.select()}
        onChange={(event) => {
          const next = event.target.value
          setTyped(next)
          const parsed = Number(next)
          if (next.trim() !== "" && !Number.isNaN(parsed)) onChange(parsed)
        }}
        onBlur={() => setTyped(null)}
        className="w-full rounded-md border border-white/15 bg-black/50 px-2 py-1.5 text-sm text-white outline-none focus:border-white/40"
      />
    </label>
  )
}

// TODO: Validate
const Toggle = ({
  label,
  count,
  checked,
  onChange,
}: {
  label: string
  count?: number
  checked: boolean
  onChange: (checked: boolean) => void
}) => (
  <label className="flex cursor-pointer items-center gap-2 text-sm text-white/75">
    <input
      type="checkbox"
      checked={checked}
      onChange={(event) => onChange(event.target.checked)}
      className="size-4 accent-emerald-400"
    />
    <span className="flex-1">{label}</span>
    {count !== undefined && (
      <span className="text-xs tabular-nums text-white/40">
        {count.toLocaleString()}
      </span>
    )}
  </label>
)

// TODO: Validate
export const filterSummary = (
  titles: StoreTitle[],
  filters: StoreFilters,
): string[] => {
  const bounds = storeBounds(titles)
  const range = (
    label: string,
    from: number,
    to: number,
    boundFrom: number,
    boundTo: number,
    unknown: boolean,
  ) =>
    from === boundFrom && to === boundTo && unknown
      ? `${label}: any`
      : `${label}: ${from} to ${to}${unknown ? "" : ", no unknown"}`
  const chosen = (
    label: string,
    selected: string[] | null,
    options: string[],
    unknown: boolean,
  ) => {
    if (selected === null || selected.length === options.length) {
      return unknown ? `${label}: any` : `${label}: any known`
    }
    if (selected.length === 0) return `${label}: none`
    return `${label}: ${selected.slice(0, 3).join(", ")}${
      selected.length > 3 ? ` +${selected.length - 3}` : ""
    }`
  }

  return [
    `${applyFilters(titles, filters).length.toLocaleString()} of ${titles.length.toLocaleString()} titles`,
    range(
      "Year",
      filters.yearFrom,
      filters.yearTo,
      bounds.yearFrom,
      bounds.yearTo,
      filters.unknownYear,
    ),
    range(
      `${filters.scoreSource === "imdb" ? "IMDb" : "TMDB"} Score`,
      filters.scoreFrom,
      filters.scoreTo,
      bounds.score[filters.scoreSource].from,
      bounds.score[filters.scoreSource].to,
      filters.unknownScore,
    ),
    range(
      `${filters.popularitySource === "imdb" ? "IMDb" : "TMDB"} Popularity`,
      filters.popularityFrom,
      filters.popularityTo,
      bounds.popularity[filters.popularitySource].from,
      bounds.popularity[filters.popularitySource].to,
      filters.unknownPopularity,
    ),
    chosen(
      "Media",
      filters.mediaTypes,
      bounds.mediaTypes,
      filters.unknownMediaType,
    ),
    chosen(
      "Original language",
      filters.originalLanguages,
      filters.originalLanguages ?? [],
      filters.unknownOriginalLanguage,
    ),
    chosen(
      "Language",
      filters.languages,
      filters.languages ?? [],
      filters.unknownLanguage,
    ),
    chosen("Genres", filters.genres, bounds.genres, filters.unknownGenre),
  ]
}

// TODO: Validate
const rangeSummary = (
  from: number,
  to: number,
  bound: { from: number; to: number },
  unknown: boolean,
) => {
  if (from === bound.from && to === bound.to) {
    return unknown ? "Any" : "Any known"
  }
  return `${from} to ${to}${unknown ? "" : ", no unknown"}`
}

// TODO: Validate
const FilterDropdown = ({
  label,
  summary,
  active,
  children,
}: {
  label: string
  summary: string
  active: boolean
  children: React.ReactNode
}) => {
  const [open, setOpen] = useState(false)

  return (
    <div className="mt-4 flex flex-col gap-2">
      <span className="text-xs font-medium uppercase tracking-wide text-white/50">
        {label}
      </span>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={`flex items-center justify-between gap-2 rounded-md border px-3 py-1.5 text-left text-sm ${
          active
            ? "border-emerald-300/40 bg-emerald-300/10 text-white"
            : "border-white/15 bg-black/50 text-white/75"
        }`}
      >
        <span className="truncate">{summary}</span>
        <ChevronDown
          className={`size-4 shrink-0 text-white/50 transition-transform ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>
      {open && (
        <div className="flex flex-col gap-2 rounded-md border border-white/10 bg-white/5 p-2">
          {children}
        </div>
      )}
    </div>
  )
}

// TODO: Validate
const OptionDropdown = ({
  label,
  options,
  selected,
  unknownLabel,
  unknownChecked,
  onSelectedChange,
  onUnknownChange,
}: {
  label: string
  options: Array<{ value: string; label: string; count?: number }>
  selected: string[] | null
  unknownLabel: string
  unknownChecked: boolean
  onSelectedChange: (selected: string[]) => void
  onUnknownChange: (checked: boolean) => void
}) => {
  const [search, setSearch] = useState("")
  const chosen = selected ?? options.map((option) => option.value)
  const chosenOptions = options.filter((option) =>
    chosen.includes(option.value),
  )
  const visible = options.filter((option) =>
    option.label.toLowerCase().includes(search.trim().toLowerCase()),
  )
  const everything = chosenOptions.length === options.length

  let summary: string
  if (everything) {
    summary = unknownChecked ? "All" : "All known"
  } else if (chosenOptions.length === 0) {
    summary = unknownChecked ? "Only unknown" : "None"
  } else if (chosenOptions.length <= 2) {
    summary = chosenOptions.map((option) => option.label).join(", ")
  } else {
    summary = `${chosenOptions.length} of ${options.length}`
  }

  return (
    <FilterDropdown
      label={label}
      summary={summary}
      active={!everything || !unknownChecked}
    >
      {options.length > 8 && (
        <input
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder={`Filter ${label.toLowerCase()}...`}
          className="w-full rounded-md border border-white/15 bg-black/50 px-2 py-1.5 text-sm text-white outline-none focus:border-white/40"
        />
      )}
      <div className="flex gap-2 text-xs">
        <button
          type="button"
          onClick={() =>
            onSelectedChange(options.map((option) => option.value))
          }
          className="rounded-full border border-white/20 px-3 py-0.5 text-white/70 hover:text-white"
        >
          All
        </button>
        <button
          type="button"
          onClick={() => onSelectedChange([])}
          className="rounded-full border border-white/20 px-3 py-0.5 text-white/70 hover:text-white"
        >
          None
        </button>
      </div>
      <div className="flex max-h-48 flex-col gap-2 overflow-y-auto pr-1">
        {visible.map((option) => (
          <Toggle
            key={option.value}
            label={option.label}
            count={option.count}
            checked={chosen.includes(option.value)}
            onChange={(checked) =>
              onSelectedChange(
                checked
                  ? [...chosen, option.value]
                  : chosen.filter((value) => value !== option.value),
              )
            }
          />
        ))}
        {visible.length === 0 && (
          <span className="text-xs text-white/40">No matches.</span>
        )}
      </div>
      <Toggle
        label={unknownLabel}
        checked={unknownChecked}
        onChange={onUnknownChange}
      />
    </FilterDropdown>
  )
}

// TODO: Validate
const Swatches = ({
  value,
  onChange,
}: {
  value: number
  onChange: (color: number) => void
}) => (
  <div className="flex flex-wrap gap-2">
    {PALETTE.map((entry) => (
      <button
        key={entry.color}
        type="button"
        title={entry.name}
        onClick={() => onChange(entry.color)}
        style={{
          backgroundColor: `#${entry.color.toString(16).padStart(6, "0")}`,
        }}
        className={`size-7 rounded-md border ${
          value === entry.color ? "border-white" : "border-white/20"
        }`}
      />
    ))}
  </div>
)

// TODO: Validate
const Choices = ({
  options,
  value,
  onChange,
}: {
  options: string[]
  value: number
  onChange: (index: number) => void
}) => (
  <div className="flex flex-wrap gap-2">
    {options.map((option, index) => (
      <button
        key={option}
        type="button"
        onClick={() => onChange(index)}
        className={`rounded-full border px-3 py-1 text-xs ${
          value === index
            ? "border-white/70 bg-white/15 text-white"
            : "border-white/20 text-white/70 hover:text-white"
        }`}
      >
        {option}
      </button>
    ))}
  </div>
)

// TODO: Validate
const Slider = ({
  value,
  min = 0,
  max,
  step,
  onChange,
}: {
  value: number
  min?: number
  max: number
  step: number
  onChange: (value: number) => void
}) => (
  <div className="flex items-center gap-3">
    <input
      type="range"
      min={min}
      max={max}
      step={step}
      value={value}
      onChange={(event) => onChange(Number(event.target.value))}
      className="h-1 flex-1 accent-emerald-400"
    />
    <span className="w-12 text-right text-xs tabular-nums text-white/70">
      {step < 1 ? value.toFixed(1) : value.toLocaleString()}
    </span>
  </div>
)

// TODO: Validate
export function StoreFilterPanel({
  titles,
  filters,
  design,
  open,
  onOpenChange,
  onApply,
  onDesign,
  hasDesignDefault,
  hasFilterDefault,
  onSaveDesignDefault,
  onSaveFilterDefault,
  onLoadDesignDefault,
  onLoadFilterDefault,
  metadata,
  onMetadata,
}: {
  titles: StoreTitle[]
  filters: StoreFilters
  design: StoreDesign
  open: boolean
  onOpenChange: (open: boolean) => void
  onApply: (filters: StoreFilters) => void
  onDesign: (design: StoreDesign) => void
  hasDesignDefault: boolean
  hasFilterDefault: boolean
  onSaveDesignDefault: (design: StoreDesign) => void
  onSaveFilterDefault: (filters: StoreFilters) => void
  onLoadDesignDefault: () => void
  onLoadFilterDefault: () => void
  metadata: "tmdb" | "source"
  onMetadata?: (metadata: "tmdb" | "source") => void
}) {
  const [draft, setDraft] = useState(filters)
  const [tab, setTab] = useState<"filters" | "design" | "audio">("filters")
  const panelRef = useRef<HTMLDivElement>(null)
  const draftRef = useRef(draft)
  const bounds = storeBounds(titles)

  draftRef.current = draft

  useEffect(() => {
    if (open) setDraft(filters)
  }, [open, filters])

  const { data: originalLanguages } = useQuery({
    queryKey: ["video-store-original-languages"],
    queryFn: fetchOriginalLanguages,
    refetchOnWindowFocus: false,
  })

  const { data: spokenLanguages } = useQuery({
    queryKey: ["video-store-spoken-languages"],
    queryFn: fetchSpokenLanguages,
    refetchOnWindowFocus: false,
  })

  const languageNames = new Map(
    [...(originalLanguages ?? []), ...(spokenLanguages ?? [])].map(
      (language) => [language.code, language.name],
    ),
  )
  // TODO: Validate
  const languageOptions = (codes: string[], counts: Map<string, number>) =>
    codes.map((code) => {
      const name = languageNames.get(code)
      return {
        value: code,
        label: name ? `${name} (${code})` : code,
        count: counts.get(code),
      }
    })
  const yearSummary = rangeSummary(
    draft.yearFrom,
    draft.yearTo,
    { from: bounds.yearFrom, to: bounds.yearTo },
    draft.unknownYear,
  )
  const scoreSummary = rangeSummary(
    draft.scoreFrom,
    draft.scoreTo,
    bounds.score[draft.scoreSource],
    draft.unknownScore,
  )
  const popularitySummary = rangeSummary(
    draft.popularityFrom,
    draft.popularityTo,
    bounds.popularity[draft.popularitySource],
    draft.unknownPopularity,
  )

  // TODO: Validate
  const close = () => {
    onApply(draftRef.current)
    onOpenChange(false)
  }

  useEffect(() => {
    if (!open) return
    // TODO: Validate
    const onPointerDown = (event: PointerEvent) => {
      if (panelRef.current?.contains(event.target as Node)) return
      onApply(draftRef.current)
      onOpenChange(false)
    }
    window.addEventListener("pointerdown", onPointerDown)
    return () => window.removeEventListener("pointerdown", onPointerDown)
  }, [open, onApply, onOpenChange])

  return (
    <>
      {!open && (
        <button
          type="button"
          onClick={() => onOpenChange(true)}
          className="absolute right-4 top-16 z-30 flex items-center gap-2 rounded-full bg-black/60 px-4 py-2 text-sm text-white/80 backdrop-blur hover:text-white"
        >
          <SlidersHorizontal className="size-4" />
          Settings
        </button>
      )}
      <div
        ref={panelRef}
        className={`absolute z-30 max-h-[80vh] overflow-y-auto rounded-xl border border-white/15 bg-black/85 p-4 text-white backdrop-blur ${
          open
            ? `right-4 top-16 ${tab === "audio" ? "w-[min(38rem,92vw)]" : "w-[min(20rem,90vw)]"}`
            : "pointer-events-none left-[-9999px] top-0 w-[38rem] opacity-0"
        }`}
      >
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold">Settings</span>
          <button
            type="button"
            onClick={close}
            className="rounded-full p-1 text-white/60 hover:text-white"
          >
            <X className="size-4" />
          </button>
        </div>

        <div className="mt-3 flex gap-1 rounded-lg bg-white/5 p-1">
          {(["filters", "design", "audio"] as const).map((entry) => (
            <button
              key={entry}
              type="button"
              onClick={() => setTab(entry)}
              className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium capitalize ${
                tab === entry ? "bg-white/15 text-white" : "text-white/60"
              }`}
            >
              {entry}
            </button>
          ))}
        </div>

        {tab === "design" && (
          <div className="flex flex-col gap-4 pt-4">
            <div className="flex flex-col gap-2">
              <span className="text-xs font-medium uppercase tracking-wide text-white/50">
                Cases
              </span>
              <Choices
                options={FORMATS}
                value={design.format}
                onChange={(format) => onDesign({ ...design, format })}
              />
            </div>
            <div className="flex flex-col gap-2">
              <span className="text-xs font-medium uppercase tracking-wide text-white/50">
                Floor
              </span>
              <Swatches
                value={design.floor}
                onChange={(floor) => onDesign({ ...design, floor })}
              />
            </div>
            <div className="flex flex-col gap-2">
              <span className="text-xs font-medium uppercase tracking-wide text-white/50">
                Walls
              </span>
              <Swatches
                value={design.room}
                onChange={(room) => onDesign({ ...design, room })}
              />
            </div>
            <div className="flex flex-col gap-2">
              <span className="text-xs font-medium uppercase tracking-wide text-white/50">
                Indoor lights
              </span>
              <Slider
                value={design.lights}
                max={5}
                step={0.1}
                onChange={(lights) => onDesign({ ...design, lights })}
              />
            </div>
            <div className="flex flex-col gap-2">
              <span className="text-xs font-medium uppercase tracking-wide text-white/50">
                Lit lamps
              </span>
              <Slider
                value={design.lamps}
                max={64}
                step={1}
                onChange={(lamps) => onDesign({ ...design, lamps })}
              />
            </div>
            <div className="flex flex-col gap-2">
              <span className="text-xs font-medium uppercase tracking-wide text-white/50">
                Outdoor lights
              </span>
              <Slider
                value={design.outdoor}
                max={5}
                step={0.1}
                onChange={(outdoor) => onDesign({ ...design, outdoor })}
              />
            </div>
            <div className="flex flex-col gap-2">
              <span className="text-xs font-medium uppercase tracking-wide text-white/50">
                Askew
              </span>
              <Slider
                value={design.askew}
                max={200}
                step={1}
                onChange={(askew) => onDesign({ ...design, askew })}
              />
            </div>
            <div className="flex flex-col gap-2">
              <span className="text-xs font-medium uppercase tracking-wide text-white/50">
                Rain drops
              </span>
              <Slider
                value={design.rainDrops}
                max={20000}
                step={200}
                onChange={(rainDrops) => onDesign({ ...design, rainDrops })}
              />
            </div>
            <div className="flex flex-col gap-2">
              <span className="text-xs font-medium uppercase tracking-wide text-white/50">
                Rain speed
              </span>
              <Slider
                value={design.rainSpeed}
                max={40}
                step={1}
                onChange={(rainSpeed) => onDesign({ ...design, rainSpeed })}
              />
            </div>
            <Toggle
              label="Shine on cases"
              checked={design.shine}
              onChange={(shine) => onDesign({ ...design, shine })}
            />
            <Toggle
              label="Cases ignore lighting"
              checked={design.unlit}
              onChange={(unlit) => onDesign({ ...design, unlit })}
            />
            <Toggle
              label="Full size posters"
              checked={design.fullPosters}
              onChange={(fullPosters) => onDesign({ ...design, fullPosters })}
            />
            <Toggle
              label="Show FPS counter"
              checked={design.fps}
              onChange={(fps) => onDesign({ ...design, fps })}
            />
            <Toggle
              label="Play trailers automatically"
              checked={design.autoplayTrailers}
              onChange={(autoplayTrailers) =>
                onDesign({ ...design, autoplayTrailers })
              }
            />
            <div className="flex items-center gap-2 text-xs">
              <button
                type="button"
                onClick={() => onSaveDesignDefault(design)}
                className="rounded-full border border-white/20 px-3 py-1 text-white/70 hover:text-white"
              >
                Set default
              </button>
              {hasDesignDefault && (
                <button
                  type="button"
                  onClick={onLoadDesignDefault}
                  className="rounded-full border border-white/20 px-3 py-1 text-white/70 hover:text-white"
                >
                  Load default
                </button>
              )}
            </div>
          </div>
        )}

        <div
          className={
            tab === "audio"
              ? "flex flex-col gap-4 pt-4"
              : "pointer-events-none absolute left-[-9999px] top-0 flex w-[34rem] flex-col gap-4 opacity-0"
          }
        >
          <span className="text-xs font-medium uppercase tracking-wide text-white/50">
            Store soundtrack
          </span>
          <iframe
            title="Store soundtrack"
            src="https://www.youtube.com/embed/qX_XTr0rN2E"
            allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            referrerPolicy="strict-origin-when-cross-origin"
            allowFullScreen
            className="aspect-video w-full rounded-lg border border-white/15"
          />
          <p className="text-[11px] text-white/40">
            Keeps playing while you browse the shelves.
          </p>
        </div>

        {tab === "filters" && (
          <>
            {onMetadata && (
              <div className="mt-4 flex flex-col gap-2">
                <span className="text-xs font-medium uppercase tracking-wide text-white/50">
                  Data
                </span>
                <Choices
                  options={["TMDB", "Website"]}
                  value={metadata === "source" ? 1 : 0}
                  onChange={(index) =>
                    onMetadata(index === 1 ? "source" : "tmdb")
                  }
                />
                <p className="text-[11px] text-white/40">
                  Where the names, years, artwork and blurbs come from.
                </p>
              </div>
            )}

            <FilterDropdown
              label="Year"
              summary={yearSummary}
              active={!yearSummary.startsWith("Any") || !draft.unknownYear}
            >
              <div className="flex gap-2">
                <NumberField
                  label="From"
                  value={draft.yearFrom}
                  onChange={(value) => setDraft({ ...draft, yearFrom: value })}
                />
                <NumberField
                  label="To"
                  value={draft.yearTo}
                  onChange={(value) => setDraft({ ...draft, yearTo: value })}
                />
              </div>
              <Toggle
                label="Include titles with no year"
                checked={draft.unknownYear}
                onChange={(checked) =>
                  setDraft({ ...draft, unknownYear: checked })
                }
              />
            </FilterDropdown>

            <FilterDropdown
              label="Score"
              summary={`${draft.scoreSource === "imdb" ? "IMDb" : "TMDB"} · ${scoreSummary}`}
              active={!scoreSummary.startsWith("Any") || !draft.unknownScore}
            >
              <Choices
                options={["TMDB", "IMDb"]}
                value={draft.scoreSource === "imdb" ? 1 : 0}
                onChange={(index) => {
                  const scoreSource = index === 1 ? "imdb" : "tmdb"
                  setDraft({
                    ...draft,
                    scoreSource,
                    scoreFrom: bounds.score[scoreSource].from,
                    scoreTo: bounds.score[scoreSource].to,
                  })
                }}
              />
              <div className="flex gap-2">
                <NumberField
                  label="From"
                  value={draft.scoreFrom}
                  onChange={(value) => setDraft({ ...draft, scoreFrom: value })}
                />
                <NumberField
                  label="To"
                  value={draft.scoreTo}
                  onChange={(value) => setDraft({ ...draft, scoreTo: value })}
                />
              </div>
              <Toggle
                label="Include titles with no score"
                checked={draft.unknownScore}
                onChange={(checked) =>
                  setDraft({ ...draft, unknownScore: checked })
                }
              />
            </FilterDropdown>

            <FilterDropdown
              label="Popularity"
              summary={`${draft.popularitySource === "imdb" ? "IMDb" : "TMDB"} · ${popularitySummary}`}
              active={
                !popularitySummary.startsWith("Any") || !draft.unknownPopularity
              }
            >
              <Choices
                options={["TMDB", "IMDb"]}
                value={draft.popularitySource === "imdb" ? 1 : 0}
                onChange={(index) => {
                  const popularitySource = index === 1 ? "imdb" : "tmdb"
                  setDraft({
                    ...draft,
                    popularitySource,
                    popularityFrom: bounds.popularity[popularitySource].from,
                    popularityTo: bounds.popularity[popularitySource].to,
                  })
                }}
              />
              <div className="flex gap-2">
                <NumberField
                  label="From"
                  value={draft.popularityFrom}
                  onChange={(value) =>
                    setDraft({ ...draft, popularityFrom: value })
                  }
                />
                <NumberField
                  label="To"
                  value={draft.popularityTo}
                  onChange={(value) =>
                    setDraft({ ...draft, popularityTo: value })
                  }
                />
              </div>
              <Toggle
                label="Include titles with no popularity"
                checked={draft.unknownPopularity}
                onChange={(checked) =>
                  setDraft({ ...draft, unknownPopularity: checked })
                }
              />
              {draft.popularitySource === "imdb" && (
                <p className="text-[11px] text-white/40">
                  IMDb popularity is a rank, so 1 is the most popular.
                </p>
              )}
            </FilterDropdown>

            <OptionDropdown
              label="Media type"
              options={bounds.mediaTypes.map((mediaType) => ({
                value: mediaType,
                label: mediaType,
                count: bounds.counts.mediaTypes.get(mediaType),
              }))}
              selected={draft.mediaTypes}
              unknownLabel={UNKNOWN_MEDIA_TYPE}
              unknownChecked={draft.unknownMediaType}
              onSelectedChange={(selected) =>
                setDraft({ ...draft, mediaTypes: selected })
              }
              onUnknownChange={(checked) =>
                setDraft({ ...draft, unknownMediaType: checked })
              }
            />

            <OptionDropdown
              label="Original language"
              options={languageOptions(
                bounds.originalLanguages,
                bounds.counts.originalLanguages,
              )}
              selected={draft.originalLanguages}
              unknownLabel="Include titles with no original language"
              unknownChecked={draft.unknownOriginalLanguage}
              onSelectedChange={(selected) =>
                setDraft({ ...draft, originalLanguages: selected })
              }
              onUnknownChange={(checked) =>
                setDraft({ ...draft, unknownOriginalLanguage: checked })
              }
            />

            <OptionDropdown
              label="Title language"
              options={languageOptions(
                bounds.languages,
                bounds.counts.languages,
              )}
              selected={draft.languages}
              unknownLabel="Include titles with no language"
              unknownChecked={draft.unknownLanguage}
              onSelectedChange={(selected) =>
                setDraft({ ...draft, languages: selected })
              }
              onUnknownChange={(checked) =>
                setDraft({ ...draft, unknownLanguage: checked })
              }
            />

            <OptionDropdown
              label="Genres"
              options={bounds.genres.map((genre) => ({
                value: genre,
                label: genre,
                count: bounds.counts.genres.get(genre),
              }))}
              selected={draft.genres}
              unknownLabel="Include titles with no genre"
              unknownChecked={draft.unknownGenre}
              onSelectedChange={(selected) =>
                setDraft({ ...draft, genres: selected })
              }
              onUnknownChange={(checked) =>
                setDraft({ ...draft, unknownGenre: checked })
              }
            />

            <div className="mt-4 flex items-center gap-2 text-xs">
              <button
                type="button"
                onClick={() => {
                  onApply(draft)
                  onSaveFilterDefault(draft)
                }}
                className="rounded-full border border-white/20 px-3 py-1 text-white/70 hover:text-white"
              >
                Set default
              </button>
              {hasFilterDefault && (
                <button
                  type="button"
                  onClick={onLoadFilterDefault}
                  className="rounded-full border border-white/20 px-3 py-1 text-white/70 hover:text-white"
                >
                  Load default
                </button>
              )}
            </div>

            <div className="mt-4 flex items-center justify-between gap-3 text-xs text-white/50">
              <span>
                {applyFilters(titles, draft).length.toLocaleString()} on the
                shelves
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setDraft(defaultFilters(titles))}
                  className="rounded-full border border-white/20 px-3 py-1 text-white/70 hover:text-white"
                >
                  Reset
                </button>
                <button
                  type="button"
                  onClick={close}
                  className="rounded-full border border-emerald-300/40 px-3 py-1 font-medium text-emerald-200 hover:bg-emerald-300/10"
                >
                  Apply
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  )
}
