// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { SlidersHorizontal, X } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import type { StoreTitle } from "./caseTexture"
import { fetchOriginalLanguages, fetchSpokenLanguages } from "./storeLanguages"

export type StoreFilters = {
  yearFrom: number
  yearTo: number
  unknownYear: boolean
  scoreFrom: number
  scoreTo: number
  unknownScore: boolean
  popularityFrom: number
  popularityTo: number
  unknownPopularity: boolean
  mediaTypes: string[]
  unknownMediaType: boolean
  originalLanguages: string[] | null
  unknownOriginalLanguage: boolean
  languages: string[] | null
  unknownLanguage: boolean
}

export const UNKNOWN_MEDIA_TYPE = "Unknown"

// TODO: Validate
export const storeBounds = (titles: StoreTitle[]) => {
  const years = titles
    .map((title) => title.year)
    .filter((year) => year !== null)
  const scores = titles
    .map((title) => title.score)
    .filter((score) => score !== null)
  const popularity = titles
    .map((title) => title.popularity)
    .filter((value) => value !== null)
  const mediaTypes = [
    ...new Set(
      titles
        .map((title) => title.mediaType)
        .filter((mediaType) => mediaType !== null),
    ),
  ].sort((left, right) => left.localeCompare(right))
  return {
    yearFrom: years.length > 0 ? Math.min(...years) : 0,
    yearTo: years.length > 0 ? Math.max(...years) : 0,
    scoreFrom: scores.length > 0 ? Math.floor(Math.min(...scores)) : 0,
    scoreTo: scores.length > 0 ? Math.ceil(Math.max(...scores)) : 0,
    popularityFrom:
      popularity.length > 0 ? Math.floor(Math.min(...popularity)) : 0,
    popularityTo:
      popularity.length > 0 ? Math.ceil(Math.max(...popularity)) : 0,
    mediaTypes,
  }
}

// TODO: Validate
export const defaultFilters = (titles: StoreTitle[]): StoreFilters => {
  const bounds = storeBounds(titles)
  return {
    yearFrom: bounds.yearFrom,
    yearTo: bounds.yearTo,
    unknownYear: true,
    scoreFrom: bounds.scoreFrom,
    scoreTo: bounds.scoreTo,
    unknownScore: true,
    popularityFrom: bounds.popularityFrom,
    popularityTo: bounds.popularityTo,
    unknownPopularity: true,
    mediaTypes: bounds.mediaTypes,
    unknownMediaType: true,
    originalLanguages: null,
    unknownOriginalLanguage: true,
    languages: null,
    unknownLanguage: true,
  }
}

// TODO: Validate
export const applyFilters = (titles: StoreTitle[], filters: StoreFilters) =>
  titles.filter((title) => {
    if (title.year === null) {
      if (!filters.unknownYear) return false
    } else if (title.year < filters.yearFrom || title.year > filters.yearTo) {
      return false
    }

    if (title.score === null) {
      if (!filters.unknownScore) return false
    } else if (
      title.score < filters.scoreFrom ||
      title.score > filters.scoreTo
    ) {
      return false
    }

    if (title.popularity === null) {
      if (!filters.unknownPopularity) return false
    } else if (
      title.popularity < filters.popularityFrom ||
      title.popularity > filters.popularityTo
    ) {
      return false
    }

    if (title.mediaType === null) {
      if (!filters.unknownMediaType) return false
    } else if (!filters.mediaTypes.includes(title.mediaType)) {
      return false
    }

    if (title.originalLanguage === null) {
      if (!filters.unknownOriginalLanguage) return false
    } else if (
      filters.originalLanguages !== null &&
      !filters.originalLanguages.includes(title.originalLanguage)
    ) {
      return false
    }

    if (title.languages.length === 0) return filters.unknownLanguage
    return (
      filters.languages === null ||
      title.languages.some((code) => filters.languages?.includes(code))
    )
  })

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
  checked,
  onChange,
}: {
  label: string
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
    {label}
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
      "Score",
      filters.scoreFrom,
      filters.scoreTo,
      bounds.scoreFrom,
      bounds.scoreTo,
      filters.unknownScore,
    ),
    range(
      "Popularity",
      filters.popularityFrom,
      filters.popularityTo,
      bounds.popularityFrom,
      bounds.popularityTo,
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
  ]
}

// TODO: Validate
const LanguageSection = ({
  label,
  options,
  selected,
  unknownLabel,
  unknownChecked,
  onSelectedChange,
  onUnknownChange,
}: {
  label: string
  options: Array<{ code: string; name: string | null }>
  selected: string[] | null
  unknownLabel: string
  unknownChecked: boolean
  onSelectedChange: (selected: string[]) => void
  onUnknownChange: (checked: boolean) => void
}) => (
  <div className="mt-4 flex flex-col gap-2">
    <span className="text-xs font-medium uppercase tracking-wide text-white/50">
      {label}
    </span>
    <div className="flex max-h-40 flex-col gap-2 overflow-y-auto pr-1">
      {options.map((option) => (
        <Toggle
          key={option.code}
          label={option.name ? `${option.name} (${option.code})` : option.code}
          checked={selected === null || selected.includes(option.code)}
          onChange={(checked) => {
            const current = selected ?? options.map((entry) => entry.code)
            onSelectedChange(
              checked
                ? [...current, option.code]
                : current.filter((code) => code !== option.code),
            )
          }}
        />
      ))}
    </div>
    <Toggle
      label={unknownLabel}
      checked={unknownChecked}
      onChange={onUnknownChange}
    />
  </div>
)

// TODO: Validate
export function StoreFilterPanel({
  titles,
  filters,
  open,
  onOpenChange,
  onApply,
}: {
  titles: StoreTitle[]
  filters: StoreFilters
  open: boolean
  onOpenChange: (open: boolean) => void
  onApply: (filters: StoreFilters) => void
}) {
  const [draft, setDraft] = useState(filters)
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

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => onOpenChange(true)}
        className="absolute right-4 top-16 z-30 flex items-center gap-2 rounded-full bg-black/60 px-4 py-2 text-sm text-white/80 backdrop-blur hover:text-white"
      >
        <SlidersHorizontal className="size-4" />
        Filters
      </button>
    )
  }

  return (
    <div
      ref={panelRef}
      className="absolute right-4 top-16 z-30 max-h-[80vh] w-[min(20rem,90vw)] overflow-y-auto rounded-xl border border-white/15 bg-black/85 p-4 text-white backdrop-blur"
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold">Filters</span>
        <button
          type="button"
          onClick={close}
          className="rounded-full p-1 text-white/60 hover:text-white"
        >
          <X className="size-4" />
        </button>
      </div>

      <div className="mt-4 flex flex-col gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-white/50">
          Year
        </span>
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
          onChange={(checked) => setDraft({ ...draft, unknownYear: checked })}
        />
      </div>

      <div className="mt-4 flex flex-col gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-white/50">
          Score
        </span>
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
          onChange={(checked) => setDraft({ ...draft, unknownScore: checked })}
        />
      </div>

      <div className="mt-4 flex flex-col gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-white/50">
          Popularity
        </span>
        <div className="flex gap-2">
          <NumberField
            label="From"
            value={draft.popularityFrom}
            onChange={(value) => setDraft({ ...draft, popularityFrom: value })}
          />
          <NumberField
            label="To"
            value={draft.popularityTo}
            onChange={(value) => setDraft({ ...draft, popularityTo: value })}
          />
        </div>
        <Toggle
          label="Include titles with no popularity"
          checked={draft.unknownPopularity}
          onChange={(checked) =>
            setDraft({ ...draft, unknownPopularity: checked })
          }
        />
      </div>

      <div className="mt-4 flex flex-col gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-white/50">
          Media type
        </span>
        {bounds.mediaTypes.map((mediaType) => (
          <Toggle
            key={mediaType}
            label={mediaType}
            checked={draft.mediaTypes.includes(mediaType)}
            onChange={(checked) =>
              setDraft({
                ...filters,
                mediaTypes: checked
                  ? [...draft.mediaTypes, mediaType]
                  : draft.mediaTypes.filter((entry) => entry !== mediaType),
              })
            }
          />
        ))}
        <Toggle
          label={UNKNOWN_MEDIA_TYPE}
          checked={draft.unknownMediaType}
          onChange={(checked) =>
            setDraft({ ...draft, unknownMediaType: checked })
          }
        />
      </div>

      <LanguageSection
        label="Original language"
        options={originalLanguages ?? []}
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

      <LanguageSection
        label="Title language"
        options={spokenLanguages ?? []}
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

      <div className="mt-4 flex items-center justify-between gap-3 text-xs text-white/50">
        <span>
          {applyFilters(titles, draft).length.toLocaleString()} on the shelves
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
    </div>
  )
}
