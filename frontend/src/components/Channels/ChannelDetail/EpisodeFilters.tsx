// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import {
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query"
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
import { type Resolver, useForm } from "react-hook-form"
import { z } from "zod"

import { getChannelEpisodes } from "@/api/channels"
import { ChannelsService, type SortKeyInput, type SourcePublic } from "@/client"
import { VariantTrigger } from "@/components/Common/VariantTrigger"
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

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
        order: z.string().optional(),
        aggregation: z.string().optional(),
        days: z.number().nullable().optional(),
        fuzziness: z.number().nullable().optional(),
      }),
    )
    .optional(),
  maximumWatchDateAbsolute: z.string().optional(),
  maximumWatchDateRelative: z.coerce.number().optional(),
  totalShowsCount: z.coerce.number().optional(),
  startedShowsCount: z.coerce.number().optional(),
  newShowsCount: z.coerce.number().optional(),
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
  sourceIds: z.array(z.string()).optional(),
  sourceIdsIsBlacklist: z.boolean().optional(),
})

type FormValues = z.infer<typeof formSchema>

type SortOption = {
  model: string
  field: string
  label: string
}

const AGGREGATION_OPTIONS = ["max", "min", "avg"] as const
type Aggregation = (typeof AGGREGATION_OPTIONS)[number]

const ORDER_OPTIONS = [
  { value: "sequential", label: "Sequential" },
  { value: "interleave", label: "Interleave" },
  { value: "randomize", label: "Randomize" },
] as const
type Order = (typeof ORDER_OPTIONS)[number]["value"]

type RecentlyAiredMode = "relative" | "absolute"

type SortEntry = {
  model: string
  field: string
  direction: "ascending" | "descending"
  order: Order
  aggregation: Aggregation | null
  days: number | null
  recentlyAiredDate: string | null
  recentlyAiredMode: RecentlyAiredMode
  fuzziness: number
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
                    order: "sequential",
                    aggregation: null,
                    days: null,
                    recentlyAiredDate: null,
                    recentlyAiredMode: "relative",
                    fuzziness: 0,
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
    sourceIds?: string[]
    sourceIdsIsBlacklist?: boolean
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
      const fuzziness =
        (input as SortKeyInput & { fuzziness?: number | null }).fuzziness ?? 0
      return {
        model: input.model ?? "episode",
        field: input.field ?? "",
        direction: (input.direction === "descending"
          ? "descending"
          : "ascending") as SortEntry["direction"],
        order: (ORDER_OPTIONS.some((option) => option.value === input.order)
          ? input.order
          : "sequential") as Order,
        aggregation: (input.aggregation as Aggregation) ?? null,
        days: input.days ?? null,
        recentlyAiredDate: input.recentlyAiredDate ?? null,
        recentlyAiredMode: (input.recentlyAiredDate
          ? "absolute"
          : "relative") as RecentlyAiredMode,
        fuzziness,
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
    resolver: zodResolver(formSchema) as Resolver<FormValues>,
    mode: "onChange",
    criteriaMode: "all",
    defaultValues: {
      hideWatched: filterParams.hideWatched,
      hideUnwatched: filterParams.hideUnwatched,
      sortBy: filterParams.sortBy as FormValues["sortBy"],
      maximumWatchDateAbsolute: filterParams.maximumWatchDateAbsolute,
      maximumWatchDateRelative: filterParams.maximumWatchDateRelative,
      totalShowsCount: filterParams.totalShowsCount,
      startedShowsCount: filterParams.startedShowsCount,
      newShowsCount: filterParams.newShowsCount,
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
      sourceIds: filterParams.sourceIds,
      sourceIdsIsBlacklist: filterParams.sourceIdsIsBlacklist,
    },
  })

  const sourceChannelIds = [
    channelId,
    ...(filterParams.additionalChannels ?? []),
  ]

  const sourcesQueries = useQueries({
    queries: sourceChannelIds.map((id) => ({
      queryKey: ["channel-sources", id],
      queryFn: () => ChannelsService.getChannelSources({ channelId: id }),
      enabled: isOpen,
      refetchOnWindowFocus: false,
    })),
  })

  const availableSources = (() => {
    const merged: Record<string, SourcePublic> = {}
    for (const query of sourcesQueries) {
      for (const source of query.data ?? []) {
        merged[source.id] = source
      }
    }
    return Object.values(merged).sort((a, b) =>
      (a.name ?? "").localeCompare(b.name ?? ""),
    )
  })()

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
      order: entry.order,
      aggregation: entry.aggregation ?? undefined,
      days:
        isRecentlyAired(entry) && entry.recentlyAiredMode === "relative"
          ? entry.days
          : undefined,
      recentlyAiredDate:
        isRecentlyAired(entry) && entry.recentlyAiredMode === "absolute"
          ? entry.recentlyAiredDate
          : undefined,
      fuzziness: entry.fuzziness > 0 ? entry.fuzziness : undefined,
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
        <VariantTrigger
          variant={variant}
          icon={Filter}
          label="Channel Options"
          menuLabel="Filters"
        />
      </DialogTrigger>
      {/* Large max width looks nicer than medium. */}
      <DialogContent className="sm:max-w-lrg max-h-[85vh] flex flex-col">
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
            className="flex flex-col gap-4 py-4 overflow-y-auto flex-1 min-h-0"
          >
            <Tabs defaultValue="filtering" className="flex-1 min-h-0 gap-4">
              <TabsList className="w-full">
                <TabsTrigger value="filtering">Filtering</TabsTrigger>
                <TabsTrigger value="sorting">Sorting</TabsTrigger>
                <TabsTrigger value="sources">Sources</TabsTrigger>
              </TabsList>
              <TabsContent value="filtering" className="space-y-4">
                {/* grid - Use a grid layout */}
                {/* md:grid-cols-2 - 2 column grid */}
                {/* gap-4 - When the columns get stacked vertically this adds spacing between them */}
                <div className="grid md:grid-cols-2 gap-4">
                  {/* space-y-4 - Space between header and text */}
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <h3>Show Counts</h3>

                      <FormField
                        control={form.control}
                        name="totalShowsCount"
                        render={({ field }) => (
                          <FormItem className="flex items-center gap-3 space-y-0">
                            <FormLabel className="font-normal w-28 shrink-0">
                              Total Shows
                            </FormLabel>
                            <FormControl>
                              <Input {...field} type="number" min={0} />
                            </FormControl>
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={form.control}
                        name="startedShowsCount"
                        render={({ field }) => (
                          <FormItem className="flex items-center gap-3 space-y-0">
                            <FormLabel className="font-normal w-28 shrink-0">
                              Started Shows
                            </FormLabel>
                            <FormControl>
                              <Input {...field} type="number" min={0} />
                            </FormControl>
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={form.control}
                        name="newShowsCount"
                        render={({ field }) => (
                          <FormItem className="flex items-center gap-3 space-y-0">
                            <FormLabel className="font-normal w-28 shrink-0">
                              New Shows
                            </FormLabel>
                            <FormControl>
                              <Input {...field} type="number" min={0} />
                            </FormControl>
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
                    <FormLabel className="text-sm font-medium">
                      Duration
                    </FormLabel>
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
              </TabsContent>
              <TabsContent value="sorting" className="space-y-4">
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
                        const isRecentlyAired =
                          entry.model === "episode" &&
                          entry.field === "recently_aired"
                        return (
                          <div
                            key={`${entry.model}.${entry.field}.${index}`}
                            className="border rounded text-sm overflow-hidden"
                          >
                            <div className="flex items-center justify-between p-2">
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
                                  className="h-7 w-7 p-0"
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
                                <span className="text-xs font-medium">
                                  {label}
                                </span>
                              </div>
                              <div className="flex items-center gap-1">
                                <Button
                                  type="button"
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => moveSortOption(index, "up")}
                                  disabled={index === 0}
                                  className="h-7 w-7 p-0"
                                >
                                  <ChevronUp className="h-3 w-3" />
                                </Button>
                                <Button
                                  type="button"
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => moveSortOption(index, "down")}
                                  disabled={index === sortEntries.length - 1}
                                  className="h-7 w-7 p-0"
                                >
                                  <ChevronDown className="h-3 w-3" />
                                </Button>
                                <Button
                                  type="button"
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => removeSortOption(index)}
                                  className="h-7 w-7 p-0 text-destructive"
                                >
                                  <X className="h-3 w-3" />
                                </Button>
                              </div>
                            </div>
                            <div className="flex flex-wrap items-center gap-2 px-2 pb-2">
                              <Select
                                value={entry.order}
                                onValueChange={(value) =>
                                  updateEntry(index, { order: value as Order })
                                }
                              >
                                <SelectTrigger className="h-9 w-auto text-sm">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  {ORDER_OPTIONS.map((option) => (
                                    <SelectItem
                                      key={option.value}
                                      value={option.value}
                                    >
                                      {option.label}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                              <Select
                                value={entry.aggregation ?? "__none__"}
                                onValueChange={(value) =>
                                  updateEntry(index, {
                                    aggregation:
                                      value === "__none__"
                                        ? null
                                        : (value as Aggregation),
                                  })
                                }
                              >
                                <SelectTrigger className="h-9 w-auto text-sm">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="__none__">
                                    No Agg
                                  </SelectItem>
                                  {AGGREGATION_OPTIONS.map((agg) => (
                                    <SelectItem key={agg} value={agg}>
                                      {agg.charAt(0).toUpperCase() +
                                        agg.slice(1)}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                              {isRecentlyAired && (
                                <>
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant="outline"
                                    onClick={() =>
                                      updateEntry(index, {
                                        recentlyAiredMode:
                                          entry.recentlyAiredMode === "relative"
                                            ? "absolute"
                                            : "relative",
                                      })
                                    }
                                    className="h-9 px-3 text-sm"
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
                                      className="h-9 w-20 text-sm"
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
                                      className="h-9 w-36 text-sm"
                                    />
                                  )}
                                </>
                              )}
                              <div className="flex items-center gap-2">
                                <Label
                                  htmlFor={`fuzziness-${index}`}
                                  className="text-xs"
                                >
                                  Fuzziness
                                </Label>
                                <Input
                                  id={`fuzziness-${index}`}
                                  type="number"
                                  min={0}
                                  value={entry.fuzziness}
                                  onChange={(event) =>
                                    updateEntry(index, {
                                      fuzziness: event.target.value
                                        ? parseInt(event.target.value, 10)
                                        : 0,
                                    })
                                  }
                                  className="h-9 w-24 text-sm"
                                />
                              </div>
                            </div>
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
              </TabsContent>
              <TabsContent value="sources" className="space-y-4">
                <FormField
                  control={form.control}
                  name="sourceIds"
                  render={({ field }) => {
                    const selected = new Set(field.value ?? [])
                    const isLoading = sourcesQueries.some(
                      (query) => query.isLoading,
                    )
                    const allIds = availableSources.map((source) => source.id)
                    const allSelected =
                      allIds.length > 0 &&
                      allIds.every((id) => selected.has(id))
                    const isBlacklist = !!form.watch("sourceIdsIsBlacklist")

                    const toggle = (id: string) => {
                      const next = new Set(selected)
                      if (next.has(id)) {
                        next.delete(id)
                      } else {
                        next.add(id)
                      }
                      field.onChange(Array.from(next))
                    }

                    return (
                      <FormItem className="space-y-3">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <FormLabel>Filter by Source</FormLabel>
                          <div className="flex items-center gap-2">
                            <FormField
                              control={form.control}
                              name="sourceIdsIsBlacklist"
                              render={({ field: modeField }) => (
                                <div className="inline-flex rounded-md border overflow-hidden">
                                  <Button
                                    type="button"
                                    variant={
                                      isBlacklist ? "ghost" : "secondary"
                                    }
                                    size="sm"
                                    className="rounded-none"
                                    onClick={() => modeField.onChange(false)}
                                  >
                                    Whitelist
                                  </Button>
                                  <Button
                                    type="button"
                                    variant={
                                      isBlacklist ? "secondary" : "ghost"
                                    }
                                    size="sm"
                                    className="rounded-none"
                                    onClick={() => modeField.onChange(true)}
                                  >
                                    Blacklist
                                  </Button>
                                </div>
                              )}
                            />
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              onClick={() =>
                                field.onChange(allSelected ? [] : allIds)
                              }
                              disabled={allIds.length === 0}
                            >
                              {allSelected ? "Clear All" : "Select All"}
                            </Button>
                          </div>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {isBlacklist
                            ? "Episodes from the selected sources will be hidden. Select none to include all sources."
                            : "Episodes are limited to the selected sources. Select none to include all sources."}
                        </p>
                        {isLoading ? (
                          <p className="text-sm text-muted-foreground">
                            Loading sources...
                          </p>
                        ) : availableSources.length === 0 ? (
                          <p className="text-sm text-muted-foreground">
                            No sources found.
                          </p>
                        ) : (
                          <div className="border rounded-lg divide-y">
                            {availableSources.map((source) => {
                              const checkboxId = `source-${source.id}`
                              return (
                                <div
                                  key={source.id}
                                  className="flex items-center gap-3 p-2 hover:bg-muted/50"
                                >
                                  <Checkbox
                                    id={checkboxId}
                                    checked={selected.has(source.id)}
                                    onCheckedChange={() => toggle(source.id)}
                                  />
                                  {source.favicon_url && (
                                    <img
                                      src={source.favicon_url}
                                      alt={`${source.name} favicon`}
                                      className="size-4"
                                    />
                                  )}
                                  <Label
                                    htmlFor={checkboxId}
                                    className="text-sm font-normal cursor-pointer flex-1"
                                  >
                                    {source.name ?? source.id}
                                  </Label>
                                </div>
                              )
                            })}
                          </div>
                        )}
                      </FormItem>
                    )
                  }}
                />
              </TabsContent>
            </Tabs>
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
