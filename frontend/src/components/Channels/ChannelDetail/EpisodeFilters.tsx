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
import { useMemo, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { ChannelsService } from "@/client"
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

import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

const formSchema = z.object({
  hideWatched: z.boolean().optional(),
  hideUnwatched: z.boolean().optional(),
  rotateShows: z.boolean().optional(),
  rotateShowsRandomly: z.boolean().optional(),
  randomizeOnLastSort: z.boolean().optional(),
  sortBy: z.array(z.string()).optional(),
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
  value: string
  label: string
}

// Oringally copied from: https://ui.shadcn.com/docs/components/combobox
function SortOptionsList({
  setOpen,
  sortOptions,
  selectedSortOptions,
  setSelectedSortOptions,
  form,
}: {
  setOpen: (open: boolean) => void
  sortOptions: SortOption[]
  selectedSortOptions: string[]
  setSelectedSortOptions: (options: string[]) => void
  form: any
}) {
  return (
    <Command>
      <CommandInput placeholder="Filter sort options..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup>
          {sortOptions.map((option) => (
            <CommandItem
              key={option.value}
              value={option.label}
              keywords={[option.value]}
              onSelect={() => {
                if (!selectedSortOptions.includes(option.value)) {
                  const newOptions = [...selectedSortOptions, option.value]
                  setSelectedSortOptions(newOptions)
                  form.setValue("sortBy", newOptions)
                }
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
  filterParams: FormValues & { additionalChannels?: string[] }
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

  // Parse existing sort options to extract field and direction
  const parseExistingSortOptions = (sortBy: string[] | undefined) => {
    if (!sortBy)
      return {
        fields: [],
        directions: new Map<string, "ascending" | "descending">(),
      }

    const fields: string[] = []
    const directions = new Map<string, "ascending" | "descending">()

    sortBy.forEach((option) => {
      const direction = option.endsWith(".ascending")
        ? "ascending"
        : "descending"
      const field = option.replace(/\.(ascending|descending)$/, "")
      fields.push(field)
      directions.set(field, direction)
    })

    return { fields, directions }
  }

  const { fields: initialFields, directions: initialDirections } =
    parseExistingSortOptions(filterParams.sortBy)

  const [selectedSortOptions, setSelectedSortOptions] =
    useState<string[]>(initialFields)
  const [sortDirections, setSortDirections] =
    useState<Map<string, "ascending" | "descending">>(initialDirections)
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [seedInputValue, setSeedInputValue] = useState(
    randomSeed !== undefined ? String(randomSeed) : "",
  )

  const navigate = useNavigate()

  const { data: sortOptionsResponse } = useQuery({
    queryKey: ["sort-options"],
    queryFn: () => ChannelsService.getSortOptions(),
    refetchOnWindowFocus: false,
    refetchOnMount: false,
  })

  const sortOptions = sortOptionsResponse?.data || []

  const form = useForm<FormValues>({
    // TODO: Fix this as any cast
    resolver: zodResolver(formSchema) as any,
    mode: "onChange",
    criteriaMode: "all",
    defaultValues: {
      hideWatched: filterParams.hideWatched,
      hideUnwatched: filterParams.hideUnwatched,
      rotateShows: filterParams.rotateShows,
      rotateShowsRandomly: filterParams.rotateShowsRandomly,
      randomizeOnLastSort: filterParams.randomizeOnLastSort,
      sortBy: filterParams.sortBy,
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
      ChannelsService.getChannelEpisodes({
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

    const sortByWithDirections = selectedSortOptions.map((field) => {
      const direction = sortDirections.get(field) || "ascending"
      return `${field}.${direction}`
    })

    // additionalChannels is managed from a different form so the value needs to be
    // extracted from the current URL then all of the other filters can be applied.
    const parsedSeed =
      seedInputValue !== "" ? parseInt(seedInputValue, 10) : undefined
    const newSearch: Record<string, any> = {
      additionalChannels: filterParams.additionalChannels,
      randomSeed: !Number.isNaN(parsedSeed as number) ? parsedSeed : randomSeed,
      ...cleanFormData({ ...filteredData, sortBy: sortByWithDirections }),
    }

    mutation.mutate(newSearch)
  }

  const moveSortOption = (index: number, direction: "up" | "down") => {
    const newSortBy = [...selectedSortOptions]
    const targetIndex = direction === "up" ? index - 1 : index + 1

    ;[newSortBy[index], newSortBy[targetIndex]] = [
      newSortBy[targetIndex],
      newSortBy[index],
    ]
    setSelectedSortOptions(newSortBy)
    form.setValue("sortBy", newSortBy)
  }

  const removeSortOption = (index: number) => {
    const newSortBy = selectedSortOptions.filter((_, i) => i !== index)
    setSelectedSortOptions(newSortBy)
    form.setValue("sortBy", newSortBy)
  }

  const toggleSortDirection = (field: string) => {
    setSortDirections((prev) => {
      const newMap = new Map(prev)
      const currentDirection = newMap.get(field) || "ascending"
      newMap.set(
        field,
        currentDirection === "ascending" ? "descending" : "ascending",
      )
      return newMap
    })
  }

  const selectedLabels = useMemo(() => {
    return selectedSortOptions
      .map((value) => {
        const option = sortOptions.find((option) => option.value === value)
        return option?.label
      })
      .filter((label): label is string => label !== undefined)
  }, [selectedSortOptions, sortOptions])

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
                <h3>Rotate Options</h3>
                <div className="space-y-2">
                  <FormField
                    control={form.control}
                    name="rotateShows"
                    render={({ field }) => (
                      <FormItem className="flex items-center gap-3 space-y-0">
                        <FormControl>
                          <Checkbox
                            checked={field.value}
                            onCheckedChange={(checked) => {
                              field.onChange(checked)
                              if (checked) {
                                form.setValue("rotateShowsRandomly", false)
                                form.setValue("randomizeOnLastSort", false)
                              }
                            }}
                          />
                        </FormControl>
                        <FormLabel className="font-normal">
                          Rotate Shows
                        </FormLabel>
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="rotateShowsRandomly"
                    render={({ field }) => (
                      <FormItem className="flex items-center gap-3 space-y-0">
                        <FormControl>
                          <Checkbox
                            checked={field.value}
                            onCheckedChange={(checked) => {
                              field.onChange(checked)
                              if (checked) {
                                form.setValue("rotateShows", false)
                                form.setValue("randomizeOnLastSort", false)
                              }
                            }}
                          />
                        </FormControl>
                        <FormLabel className="font-normal">
                          Randomize Shows
                        </FormLabel>
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="randomizeOnLastSort"
                    render={({ field }) => (
                      <FormItem className="flex items-center gap-3 space-y-0">
                        <FormControl>
                          <Checkbox
                            checked={field.value}
                            onCheckedChange={(checked) => {
                              field.onChange(checked)
                              if (checked) {
                                form.setValue("rotateShows", false)
                                form.setValue("rotateShowsRandomly", false)
                              }
                            }}
                          />
                        </FormControl>
                        <FormLabel className="font-normal">
                          Randomize on Last Sort
                        </FormLabel>
                      </FormItem>
                    )}
                  />

                  <h3 className="pt-4">Show Status</h3>

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
                <h3>Watch Options</h3>
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
                      selectedSortOptions={selectedSortOptions}
                      setSelectedSortOptions={setSelectedSortOptions}
                      form={form}
                    />
                  </PopoverContent>
                </Popover>
              </div>

              {/* TODO: The styling here could be improved */}
              {selectedLabels.length > 0 && (
                <div className="space-y-2 mt-2">
                  <Label className="text-xs text-muted-foreground">
                    Selected Sort Options (in order):
                  </Label>
                  {selectedLabels.map((label, index) => {
                    const field = selectedSortOptions[index]
                    const direction = sortDirections.get(field) || "ascending"
                    return (
                      <div
                        key={field}
                        className="flex items-center justify-between p-2 border rounded text-sm"
                      >
                        <div className="flex items-center gap-2">
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            onClick={() => toggleSortDirection(field)}
                            className="h-6 w-6 p-0"
                            title={
                              direction === "ascending"
                                ? "Ascending"
                                : "Descending"
                            }
                          >
                            {direction === "ascending" ? (
                              <ArrowUp className="h-3 w-3" />
                            ) : (
                              <ArrowDown className="h-3 w-3" />
                            )}
                          </Button>
                          <span className="text-xs">{label}</span>
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
                            disabled={index === selectedLabels.length - 1}
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
                    )
                  })}
                </div>
              )}
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
