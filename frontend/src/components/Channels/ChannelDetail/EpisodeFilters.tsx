// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"
import {
  ArrowDown,
  ArrowUp,
  ChevronDown,
  ChevronUp,
  Filter,
  Shuffle,
  X,
} from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { getChannelEpisodes } from "@/api/channels"
import { ChannelsService, type SortKeyInput } from "@/client"
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { DropdownMenuItem } from "@/components/ui/dropdown-menu"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

const formSchema = z.object({
  hideWatched: z.boolean().optional(),
  hideUnwatched: z.boolean().optional(),

  sortBy: z
    .array(
      z.object({
        model: z.string(),
        field: z.string(),
        direction: z.string().optional(),
        mode: z.string().optional(),
        aggregation: z.string().optional(),
        days: z.number().nullable().optional(),
      }),
    )
    .optional(),
  maximumWatchDateAbsolute: z.string().optional(),
  maximumWatchDateRelative: z.coerce.number().optional(),
  onlyStartedShows: z.boolean().optional(),
  onlyNewShows: z.boolean().optional(),
  minimumAirDateAbsolute: z.string().optional(),
  minimumAirDateRelative: z.coerce.number().optional(),
  maximumAirDateAbsolute: z.string().optional(),
  maximumAirDateRelative: z.coerce.number().optional(),
  minimumReleaseDateAbsolute: z.string().optional(),
  minimumReleaseDateRelative: z.coerce.number().optional(),
  maximumReleaseDateAbsolute: z.string().optional(),
  maximumReleaseDateRelative: z.coerce.number().optional(),
  minimumDuration: z.coerce.number().optional(),
  maximumDuration: z.coerce.number().optional(),
  additionalChannels: z.array(z.string()).optional(),
})

type FormValues = z.infer<typeof formSchema>

type SortOption = {
  model: string
  field: string
  label: string
}

const AGGREGATION_OPTIONS = ["sum", "avg", "count", "max", "min"] as const
type Aggregation = (typeof AGGREGATION_OPTIONS)[number]

const MODE_OPTIONS = [
  { value: "normal", label: "Normal" },
  { value: "interleave_sequential", label: "Interleave (Sequential)" },
  { value: "interleave_random", label: "Interleave (Random)" },
  { value: "group_by_show", label: "Group by Show" },
] as const
type Mode = (typeof MODE_OPTIONS)[number]["value"]

type RecentlyAiredMode = "relative" | "absolute"

type SortEntry = {
  model: string
  field: string
  direction: "ascending" | "descending"
  mode: Mode
  aggregation: Aggregation
  days: number | null
  recentlyAiredDate: string | null
  recentlyAiredMode: RecentlyAiredMode
}

// Oringally copied from: https://ui.shadcn.com/docs/components/combobox
function SortOptionsList({
  setOpen,
  sortOptions,
  setSortEntries,
}: {
  setOpen: (open: boolean) => void
  sortOptions: SortOption[]
  setSortEntries: React.Dispatch<React.SetStateAction<SortEntry[]>>
}) {
  return (
    <Command>
      <CommandInput placeholder="Filter sort options..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup>
          {sortOptions.map((option) => (
            <CommandItem
              key={`${option.model}.${option.field}`}
              value={option.label}
              keywords={[option.model, option.field]}
              onSelect={() => {
                setSortEntries((prev) => [
                  ...prev,
                  {
                    model: option.model,
                    field: option.field,
                    direction: "ascending",
                    mode: "normal",
                    aggregation: "sum",
                    days: null,
                    recentlyAiredDate: null,
                    recentlyAiredMode: "relative",
                  },
                ])
                setOpen(false)
              }}
            >
              {option.label}
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </Command>
  )
}

function cleanFormData(data: FormValues): FormValues {
  const cleaned: FormValues = {}
  Object.entries(data).forEach(([key, value]) => {
    // Ignore false values because everything is false by default
    if (value === false) return
    // If a date filter is removed it will leave a blank string which can be ignored
    if (value === "") return
    // Ignore undefined values because they are junk
    if (value === undefined) return
    // If all sort options are removed an empty array is left which can be ignored
    if (Array.isArray(value) && value.length === 0) return
    // Ignore 0 values because it means an empty string in a number field
    if (value === 0) return

    cleaned[key as keyof FormValues] = value as any
  })
  return cleaned
}

// RenderFormFieldInput is defined inside `EpisodeFilters` below so it can
// close over `dateInputModes` and `toggleDateMode` without requiring callers
// to pass an `onLabelClick` callback.

interface EpisodeFiltersProps {
  filterParams: Omit<FormValues, "sortBy"> & {
    sortBy?: SortKeyInput[]
    additionalChannels?: string[]
  }
  routeFullPath: string
  channelId: string
  randomSeed?: number
  variant?: "button" | "menu"
}

export function EpisodeFilters({
  filterParams,
  routeFullPath,
  channelId,
  randomSeed,
  variant = "button",
}: EpisodeFiltersProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  // Tracks when the dialog is open
  const [isOpen, setIsOpen] = useState(false)

  // Track which date format is being used so only the visible fields are submitted
  const [dateInputModes, setDateInputModes] = useState({
    watchDate:
      filterParams.maximumWatchDateRelative !== undefined
        ? "relative"
        : "absolute",
    airDate:
      filterParams.minimumAirDateRelative !== undefined ||
      filterParams.maximumAirDateRelative !== undefined
        ? "relative"
        : "absolute",
    releaseDate:
      filterParams.minimumReleaseDateRelative !== undefined ||
      filterParams.maximumReleaseDateRelative !== undefined
        ? "relative"
        : "absolute",
  } as Record<string, "absolute" | "relative">)

  // Toggle between absolute and relative date input modes
  const toggleDateMode = (category: string) => {
    setDateInputModes((prev) => ({
      ...prev,
      [category]: prev[category] === "absolute" ? "relative" : "absolute",
    }))
  }

  // Helper component local to EpisodeFilters so it can access toggleDateMode
  // and dateInputModes without requiring callers to pass an onLabelClick.
  function RenderFormFieldInput<T extends keyof FormValues>(props: {
    keyProp?: string
    control: any
    name?: T | string
    baseName?: string // base name like "maximumWatchDate" used with date modes
    dateModeCategory?: string
    inputType?: string
    label?: string
  }) {
    const {
      keyProp,
      control,
      name,
      baseName,
      dateModeCategory,
      inputType,
      label,
    } = props

    // Determine the input type. If not passed explicitly, infer from the
    // date mode (absolute -> date, relative -> number). Default to "text".
    const resolvedInputType =
      inputType ??
      (dateModeCategory
        ? dateInputModes[dateModeCategory] === "absolute"
          ? "date"
          : "number"
        : "text")

    const computedPlaceholder =
      resolvedInputType === "number" ? "Days ago" : undefined

    // Determine the actual form field name. If a baseName and dateModeCategory
    // are provided, select between Absolute/Relative suffixes internally.
    const resolvedName = baseName
      ? `${baseName}${dateInputModes?.[dateModeCategory || ""] === "absolute" ? "Absolute" : "Relative"}`
      : (name as string)

    const resolvedKey = keyProp ?? resolvedName

    return (
      <FormField
        key={resolvedKey}
        control={control}
        name={resolvedName as any}
        render={({ field }) => (
          <FormItem>
            {label ? (
              <FormLabel
                onClick={
                  dateModeCategory
                    ? () => toggleDateMode(dateModeCategory)
                    : undefined
                }
                className="cursor-pointer hover:text-primary underline decoration-dotted"
              >
                {label}
              </FormLabel>
            ) : null}
            <FormControl>
              <Input
                {...field}
                type={resolvedInputType}
                placeholder={computedPlaceholder}
              />
            </FormControl>
          </FormItem>
        )}
      />
    )
  }

  const parseSortEntries = (
    sortBy: SortKeyInput[] | undefined,
  ): SortEntry[] => {
    if (!sortBy) return []

    return sortBy.map((input) => {
      return {
        model: input.model ?? "episode",
        field: input.field ?? "",
        direction: (input.direction === "descending"
          ? "descending"
          : "ascending") as SortEntry["direction"],
        mode: (MODE_OPTIONS.some((o) => o.value === input.mode)
          ? input.mode
          : "normal") as Mode,
        aggregation: (input.aggregation ?? "sum") as Aggregation,
        days: input.days ?? null,
        recentlyAiredDate: input.recentlyAiredDate ?? null,
        recentlyAiredMode: (input.recentlyAiredDate
          ? "absolute"
          : "relative") as RecentlyAiredMode,
      }
    })
  }

  const [sortEntries, setSortEntries] = useState<SortEntry[]>(
    parseSortEntries(filterParams.sortBy),
  )
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [seedInputValue, setSeedInputValue] = useState(
    randomSeed !== undefined ? String(randomSeed) : "",
  )

  const navigate = useNavigate()

  const { data: sortOptions = [] } = useQuery({
    queryKey: ["sort-options"],
    queryFn: () => ChannelsService.getSortOptions(),
    refetchOnWindowFocus: false,
    refetchOnMount: false,
  })

  const form = useForm<FormValues>({
    // TODO: Fix this as any cast
    resolver: zodResolver(formSchema) as any,
    mode: "onChange",
    criteriaMode: "all",
    defaultValues: {
      hideWatched: filterParams.hideWatched,
      hideUnwatched: filterParams.hideUnwatched,
      sortBy: filterParams.sortBy as FormValues["sortBy"],
      maximumWatchDateAbsolute: filterParams.maximumWatchDateAbsolute,
      maximumWatchDateRelative: filterParams.maximumWatchDateRelative,
      onlyStartedShows: filterParams.onlyStartedShows,
      onlyNewShows: filterParams.onlyNewShows,
      minimumAirDateAbsolute: filterParams.minimumAirDateAbsolute,
      minimumAirDateRelative: filterParams.minimumAirDateRelative,
      maximumAirDateAbsolute: filterParams.maximumAirDateAbsolute,
      maximumAirDateRelative: filterParams.maximumAirDateRelative,
      minimumReleaseDateAbsolute: filterParams.minimumReleaseDateAbsolute,
      minimumReleaseDateRelative: filterParams.minimumReleaseDateRelative,
      maximumReleaseDateAbsolute: filterParams.maximumReleaseDateAbsolute,
      maximumReleaseDateRelative: filterParams.maximumReleaseDateRelative,
      minimumDuration: filterParams.minimumDuration,
      maximumDuration: filterParams.maximumDuration,
    },
  })

  const mutation = useMutation({
    mutationFn: (newSearch: Record<string, any>) =>
      getChannelEpisodes({
        channelId,
        ...newSearch,
      }),
    onSuccess: (newData, newSearch) => {
      queryClient.setQueryData(["episodes", channelId], newData)
      setIsOpen(false)
      navigate({ to: routeFullPath, search: newSearch as any, replace: true })
      showSuccessToast("Filters applied successfully")
    },
    onError: handleError.bind(showErrorToast),
  })

  const onSubmit = (data: FormValues) => {
    // Filter out unused date values that are not currently visible on the screen
    const filteredData = { ...data }
    if (dateInputModes.watchDate === "absolute") {
      delete filteredData.maximumWatchDateRelative
    } else {
      delete filteredData.maximumWatchDateAbsolute
    }

    if (dateInputModes.airDate === "absolute") {
      delete filteredData.minimumAirDateRelative
      delete filteredData.maximumAirDateRelative
    } else {
      delete filteredData.minimumAirDateAbsolute
      delete filteredData.maximumAirDateAbsolute
    }

    if (dateInputModes.releaseDate === "absolute") {
      delete filteredData.minimumReleaseDateRelative
      delete filteredData.maximumReleaseDateRelative
    } else {
      delete filteredData.minimumReleaseDateAbsolute
      delete filteredData.maximumReleaseDateAbsolute
    }

    const isRecentlyAired = (entry: SortEntry) =>
      entry.model === "episode" && entry.field === "recently_aired"

    const sortByEntries = sortEntries.map((entry) => ({
      model: entry.model,
      field: entry.field,
      direction: entry.direction,
      mode: entry.mode,
      aggregation:
        entry.mode === "group_by_show" ? entry.aggregation : undefined,
      days:
        isRecentlyAired(entry) && entry.recentlyAiredMode === "relative"
          ? entry.days
          : undefined,
      recentlyAiredDate:
        isRecentlyAired(entry) && entry.recentlyAiredMode === "absolute"
          ? entry.recentlyAiredDate
          : undefined,
    }))

    // additionalChannels is managed from a different form so the value needs to be
    // extracted from the current URL then all of the other filters can be applied.
    const parsedSeed =
      seedInputValue !== "" ? parseInt(seedInputValue, 10) : undefined
    const newSearch: Record<string, any> = {
      additionalChannels: filterParams.additionalChannels,
      randomSeed: !Number.isNaN(parsedSeed as number) ? parsedSeed : randomSeed,
      ...cleanFormData({ ...filteredData, sortBy: sortByEntries }),
    }

    mutation.mutate(newSearch)
  }

  const updateEntry = (index: number, updates: Partial<SortEntry>) => {
    setSortEntries((prev) =>
      prev.map((entry, i) => (i === index ? { ...entry, ...updates } : entry)),
    )
  }

  const moveSortOption = (index: number, direction: "up" | "down") => {
    setSortEntries((prev) => {
      const entries = [...prev]
      const targetIndex = direction === "up" ? index - 1 : index + 1
      ;[entries[index], entries[targetIndex]] = [
        entries[targetIndex],
        entries[index],
      ]
      return entries
    })
  }

  const removeSortOption = (index: number) => {
    setSortEntries((prev) => prev.filter((_, i) => i !== index))
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        {variant === "menu" ? (
          <DropdownMenuItem
            onSelect={(e) => {
              e.preventDefault()
            }}
          >
            <Filter className="mr-2 size-4" />
            Filters
          </DropdownMenuItem>
        ) : (
          <Button className="mt-2 mb-4">
            <Filter className="mr-2" />
            Channel Options
          </Button>
        )}
      </DialogTrigger>
      {/* Large max width looks nicer than medium. */}
      <DialogContent className="sm:max-w-lrg">
        <DialogHeader>
          <DialogTitle>Channel Options</DialogTitle>
          <DialogDescription>
            Configure channel filters and sorting options
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          {/* onSubmit is needed to manage additionalChannels and URL redirection */}
          <form
            onSubmit={form.handleSubmit((data) => onSubmit(data))}
            className="grid gap-4 py-4"
          >
            {/* grid - Use a grid layout */}
            {/* md:grid-cols-2 - 2 column grid */}
            {/* gap-4 - When the columns get stacked vertically this adds spacing between them */}
            <div className="grid md:grid-cols-2 gap-4">
              {/* space-y-4 - Space between header and text */}
              <div className="space-y-4">
                <div className="space-y-2">
                  <h3>Show Status Filters</h3>

                  <FormField
                    control={form.control}
                    name="onlyStartedShows"
                    render={({ field }) => (
                      <FormItem className="flex items-center gap-3 space-y-0">
                        <FormControl>
                          <Checkbox
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                        <FormLabel className="font-normal">
                          Only Started Shows
                        </FormLabel>
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="onlyNewShows"
                    render={({ field }) => (
                      <FormItem className="flex items-center gap-3 space-y-0">
                        <FormControl>
                          <Checkbox
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                        <FormLabel className="font-normal">
                          Only New Shows
                        </FormLabel>
                      </FormItem>
                    )}
                  />
                </div>
              </div>

              {/* space-y-4 - Space between header and text */}
              <div className="space-y-4">
                <h3>Watch Filters</h3>
                <div className="space-y-2">
                  <FormField
                    control={form.control}
                    name="hideUnwatched"
                    render={({ field }) => (
                      <FormItem className="flex items-center gap-3 space-y-0">
                        <FormControl>
                          <Checkbox
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                        <FormLabel className="font-normal">
                          Hide Unwatched Episodes
                        </FormLabel>
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="hideWatched"
                    render={({ field }) => (
                      <FormItem className="flex items-center gap-3 space-y-0">
                        <FormControl>
                          <Checkbox
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                        <FormLabel className="font-normal">
                          Hide Watched Episodes
                        </FormLabel>
                      </FormItem>
                    )}
                  />
                  <RenderFormFieldInput
                    baseName="maximumWatchDate"
                    dateModeCategory="watchDate"
                    control={form.control}
                    label="Minimum Watch Date"
                  />
                </div>
              </div>
            </div>
            {/* space-y-4 - Space between header and text */}
            <div className="space-y-4">
              <h3>Episode Filters</h3>
              {/* grid-cols-[80px_1fr_1fr] - Set the width of the first grid to be 80 pixels and the other 2 are dynamic */}
              <div className="grid grid-cols-[80px_1fr_1fr] gap-4">
                <div />
                <Label className="text-sm font-medium">Minimum</Label>
                <Label className="text-sm font-medium">Maximum</Label>
              </div>

              {/* Airing Date */}
              {/* grid-cols-[80px_1fr_1fr] - Set the width of the first grid to be 80 pixels and the other 2 are dynamic */}
              <div className="grid grid-cols-[80px_1fr_1fr] gap-4">
                <FormLabel
                  onClick={() => toggleDateMode("airDate")}
                  className="text-sm font-medium cursor-pointer hover:text-primary underline decoration-dotted"
                >
                  Airing Date
                </FormLabel>

                <RenderFormFieldInput
                  baseName="minimumAirDate"
                  dateModeCategory="airDate"
                  control={form.control}
                />
                <RenderFormFieldInput
                  baseName="maximumAirDate"
                  dateModeCategory="airDate"
                  control={form.control}
                />
              </div>

              {/* grid-cols-[80px_1fr_1fr] - Set the width of the first grid to be 80 pixels and the other 2 are dynamic */}
              <div className="grid grid-cols-[80px_1fr_1fr] gap-4">
                <FormLabel
                  onClick={() => toggleDateMode("releaseDate")}
                  className="text-sm font-medium cursor-pointer hover:text-primary underline decoration-dotted"
                >
                  Release Date
                </FormLabel>

                <RenderFormFieldInput
                  baseName="minimumReleaseDate"
                  dateModeCategory="releaseDate"
                  control={form.control}
                />
                <RenderFormFieldInput
                  baseName="maximumReleaseDate"
                  dateModeCategory="releaseDate"
                  control={form.control}
                />
              </div>

              {/* grid-cols-[80px_1fr_1fr] - Set the width of the first grid to be 80 pixels and the other 2 are dynamic */}
              <div className="grid grid-cols-[80px_1fr_1fr] gap-4">
                <FormLabel className="text-sm font-medium">Duration</FormLabel>
                <FormField
                  control={form.control}
                  name="minimumDuration"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <Input
                          {...field}
                          type="number"
                          placeholder="Min seconds"
                        />
                      </FormControl>
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="maximumDuration"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <Input
                          {...field}
                          type="number"
                          placeholder="Max seconds"
                        />
                      </FormControl>
                    </FormItem>
                  )}
                />
              </div>
            </div>

            <div className="space-y-4">
              <h3>Sort Options</h3>
              <div className="flex items-center gap-4">
                <Label>Sort By</Label>
                {/* Mostly copied from: https://ui.shadcn.com/docs/components/combobox */}
                <Popover open={filtersOpen} onOpenChange={setFiltersOpen}>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      role="combobox"
                      className="flex-1 justify-start"
                    >
                      Select sort option
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent
                    className="w-[400px] p-0"
                    align="start"
                    onWheel={(e) => e.stopPropagation()}
                  >
                    <SortOptionsList
                      setOpen={setFiltersOpen}
                      sortOptions={sortOptions}
                      setSortEntries={setSortEntries}
                    />
                  </PopoverContent>
                </Popover>
              </div>

              {sortEntries.length > 0 && (
                <div className="space-y-2 mt-2">
                  <Label className="text-xs text-muted-foreground">
                    Selected Sort Options (in order):
                  </Label>
                  {sortEntries.map((entry, index) => {
                    const sortOption = sortOptions.find(
                      (option) =>
                        option.model === entry.model &&
                        option.field === entry.field,
                    )
                    const label = sortOption?.label ?? entry.field
                    return (
                      <div key={index}>
                        <div
                          className={`flex items-center justify-between p-2 border text-sm ${entry.model === "episode" && entry.field === "recently_aired" ? "rounded-t" : "rounded"}`}
                        >
                          <div className="flex items-center gap-2">
                            <Button
                              type="button"
                              size="sm"
                              variant="outline"
                              onClick={() =>
                                updateEntry(index, {
                                  direction:
                                    entry.direction === "ascending"
                                      ? "descending"
                                      : "ascending",
                                })
                              }
                              className="h-6 w-6 p-0"
                              title={
                                entry.direction === "ascending"
                                  ? "Ascending"
                                  : "Descending"
                              }
                            >
                              {entry.direction === "ascending" ? (
                                <ArrowUp className="h-3 w-3" />
                              ) : (
                                <ArrowDown className="h-3 w-3" />
                              )}
                            </Button>
                            <span className="text-xs">{label}</span>
                            <Select
                              value={entry.mode}
                              onValueChange={(value) =>
                                updateEntry(index, { mode: value as Mode })
                              }
                            >
                              <SelectTrigger className="h-6 w-auto text-xs">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {MODE_OPTIONS.map((option) => (
                                  <SelectItem
                                    key={option.value}
                                    value={option.value}
                                  >
                                    {option.label}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            {entry.mode === "group_by_show" && (
                              <Select
                                value={entry.aggregation}
                                onValueChange={(value) =>
                                  updateEntry(index, {
                                    aggregation: value as Aggregation,
                                  })
                                }
                              >
                                <SelectTrigger className="h-6 w-20 text-xs">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  {AGGREGATION_OPTIONS.map((agg) => (
                                    <SelectItem key={agg} value={agg}>
                                      {agg.charAt(0).toUpperCase() +
                                        agg.slice(1)}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            )}
                          </div>
                          <div className="flex items-center gap-1">
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              onClick={() => moveSortOption(index, "up")}
                              disabled={index === 0}
                              className="h-6 w-6 p-0"
                            >
                              <ChevronUp className="h-3 w-3" />
                            </Button>
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              onClick={() => moveSortOption(index, "down")}
                              disabled={index === sortEntries.length - 1}
                              className="h-6 w-6 p-0"
                            >
                              <ChevronDown className="h-3 w-3" />
                            </Button>
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              onClick={() => removeSortOption(index)}
                              className="h-6 w-6 p-0 text-destructive"
                            >
                              <X className="h-3 w-3" />
                            </Button>
                          </div>
                        </div>
                        {entry.model === "episode" &&
                          entry.field === "recently_aired" && (
                            <div className="flex items-center gap-2 p-2 border-x border-b rounded-b text-xs">
                              <Button
                                type="button"
                                size="sm"
                                variant="ghost"
                                onClick={() =>
                                  updateEntry(index, {
                                    recentlyAiredMode:
                                      entry.recentlyAiredMode === "relative"
                                        ? "absolute"
                                        : "relative",
                                  })
                                }
                                className="h-6 text-xs px-2"
                              >
                                {entry.recentlyAiredMode === "relative"
                                  ? "Days ago"
                                  : "Since date"}
                              </Button>
                              {entry.recentlyAiredMode === "relative" ? (
                                <Input
                                  type="number"
                                  min={1}
                                  placeholder="7"
                                  value={entry.days ?? ""}
                                  onChange={(event) =>
                                    updateEntry(index, {
                                      days: event.target.value
                                        ? parseInt(event.target.value, 10)
                                        : null,
                                    })
                                  }
                                  className="h-6 w-20 text-xs"
                                />
                              ) : (
                                <Input
                                  type="date"
                                  value={entry.recentlyAiredDate ?? ""}
                                  onChange={(event) =>
                                    updateEntry(index, {
                                      recentlyAiredDate:
                                        event.target.value || null,
                                    })
                                  }
                                  className="h-6 w-36 text-xs"
                                />
                              )}
                            </div>
                          )}
                      </div>
                    )
                  })}
                </div>
              )}
              <div className="flex items-center gap-2">
                <Label htmlFor="random-seed">Random Seed</Label>
                <Input
                  id="random-seed"
                  type="number"
                  min={0}
                  value={seedInputValue}
                  onChange={(e) => setSeedInputValue(e.target.value)}
                  className="w-36 h-8 text-sm"
                  placeholder="Seed value"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  title="Generate a new random seed"
                  onClick={() =>
                    setSeedInputValue(
                      String(Math.floor(Math.random() * 2 ** 31)),
                    )
                  }
                >
                  <Shuffle className="size-4" />
                </Button>
              </div>
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsOpen(false)}
                disabled={mutation.isPending}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? "Applying..." : "Apply Filters"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
