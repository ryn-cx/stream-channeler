// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { PaginationState } from "@tanstack/react-table"
import {
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react"

import type { ChannelListOutput } from "@/client"
import { formatDuration } from "@/components/ChannelCommon/formatters"
import { useEpisodeActions } from "@/components/ChannelCommon/useEpisodeActions"
import type { EpisodeWithDetails } from "@/components/Channels/ChannelDetail/columns"
import { ChannelSearchInput } from "@/components/Channels/ChannelList/ChannelSearchInput"
import {
  type BrowseChannel,
  sortChannelsByNumber,
} from "@/components/Channels/ChannelList/ChannelsBrowse"
import { channelSearchName } from "@/components/Channels/ChannelList/ChannelsBrowseSection"
import {
  parseDefaultOrder,
  useChannelEpisodePreview,
  usePrefetchNeighborPageEpisodes,
} from "@/components/Channels/ChannelList/useChannelEpisodePreview"
import { BrowsePagination } from "@/components/Common/BrowsePagination"
import { Favicon } from "@/components/Common/Favicon"
import { ResponsiveActionMenu } from "@/components/Common/ResponsiveActionMenu"
import { Skeleton } from "@/components/ui/skeleton"
import useAuth from "@/hooks/useAuth"
import { useMarkWatched } from "@/hooks/useMarkEpisodeWatched"
import { useIsTouchDevice } from "@/hooks/useMobile"
import { cn } from "@/lib/utils"

interface GuideProgram {
  episode: EpisodeWithDetails
  startMinute: number
  minutes: number
}

interface GuideSelection {
  channelId: string
  channelName: string
  program: GuideProgram
}

// TODO: Validate
function scheduleEpisodes(episodes: EpisodeWithDetails[]): GuideProgram[] {
  const programs: GuideProgram[] = []
  let startMinute = 0
  for (const episode of episodes) {
    const minutes = Math.max(5, Math.round((episode.duration ?? 1800) / 60))
    programs.push({ episode, startMinute, minutes })
    startMinute += minutes
  }
  return programs
}

// TODO: Validate
function slotTime(date: Date): string {
  return date
    .toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })
    .replace(" ", "")
}

// TODO: Validate
function guideWindowStart(): Date {
  const start = new Date()
  start.setMinutes(start.getMinutes() < 30 ? 0 : 30, 0, 0)
  return start
}

// TODO: Validate
function GuideTable({
  windowStart,
  timelineMinutes,
  pixelsPerMinute,
  children,
}: {
  windowStart: Date
  timelineMinutes: number
  pixelsPerMinute: number
  children: ReactNode
}) {
  const slots = Array.from(
    { length: timelineMinutes / 30 },
    (_, index) => new Date(windowStart.getTime() + index * 30 * 60_000),
  )
  const nowOffset =
    ((Date.now() - windowStart.getTime()) / 60_000) * pixelsPerMinute

  return (
    <div className="overflow-x-auto rounded-md border bg-card">
      <div className="min-w-max">
        <div className="flex border-b bg-muted/50">
          <div className="sticky left-0 z-20 w-44 shrink-0 border-r bg-muted px-3 py-2 text-sm font-semibold">
            Channel
          </div>
          <div
            className="flex"
            style={{ width: timelineMinutes * pixelsPerMinute }}
          >
            {slots.map((slot) => (
              <div
                key={slot.getTime()}
                className="shrink-0 border-l px-2 py-2 text-xs font-medium text-muted-foreground tabular-nums"
                style={{ width: 30 * pixelsPerMinute }}
              >
                {`${slot.getMonth() + 1}/${slot.getDate()} ${slotTime(slot)}`}
              </div>
            ))}
          </div>
        </div>

        <div className="relative">
          <div
            className="pointer-events-none absolute top-0 bottom-0 z-10 w-px bg-destructive"
            style={{ left: 176 + nowOffset }}
          />
          {children}
        </div>
      </div>
    </div>
  )
}

// TODO: Validate
export function PendingChannelGuide({ rowCount }: { rowCount: number }) {
  const windowStart = useMemo(guideWindowStart, [])
  const pixelsPerMinute = 6
  const timelineMinutes = 240

  return (
    <div className="px-[4%] pb-8">
      <div className="pb-4">
        <Skeleton className="h-9 max-w-sm" />
      </div>

      <Skeleton className="mb-2 h-32 rounded-md" />

      <GuideTable
        windowStart={windowStart}
        timelineMinutes={timelineMinutes}
        pixelsPerMinute={pixelsPerMinute}
      >
        {Array.from({ length: rowCount }).map((_, index) => (
          <div
            key={`pending-channel-${index}`}
            className="flex border-b last:border-b-0"
          >
            <div className="sticky left-0 z-20 flex w-44 shrink-0 items-center gap-2 border-r bg-card px-3 py-2">
              <Skeleton className="h-4 w-28" />
            </div>
            <div
              className="h-16"
              style={{ width: timelineMinutes * pixelsPerMinute }}
            />
          </div>
        ))}
      </GuideTable>
    </div>
  )
}

// TODO: Validate
function episodeLabel(episode: EpisodeWithDetails): string {
  if (episode.title.media_type === "Movie") return "Movie"
  const isLinked = episode.tmdb_episode_id !== episode.id
  const seasonNumber = isLinked
    ? episode.tmdb_season_number
    : episode.season.season_number
  const number = isLinked ? episode.tmdb_episode_number : episode.episode_number
  const numbering =
    seasonNumber != null && number != null
      ? `S${seasonNumber} Ep${number}`
      : number != null
        ? `Ep${number}`
        : null
  return [numbering, episode.name].filter(Boolean).join(" · ")
}

interface GuideRowProps {
  channel: BrowseChannel
  timelineMinutes: number
  pixelsPerMinute: number
  showChannelNumber: boolean
  selectedEpisodeId: string | null
  isTouchDevice: boolean
  hideWhenEmpty: boolean
  onHighlight: (selection: GuideSelection) => void
  onMeasure: (channelId: string, minutes: number) => void
}

// TODO: Validate
function FetchedGuideRow(props: GuideRowProps) {
  const { defaultOrder, episodes, isLoading, loadFailed } =
    useChannelEpisodePreview(props.channel)
  return (
    <GuideRow
      {...props}
      defaultOrder={defaultOrder}
      episodes={episodes}
      isLoading={isLoading}
      loadFailed={loadFailed}
    />
  )
}

// TODO: Validate
function PreloadedGuideRow({
  preloaded,
  ...props
}: GuideRowProps & { preloaded: EpisodeWithDetails[] }) {
  return (
    <GuideRow
      {...props}
      defaultOrder={parseDefaultOrder(props.channel)}
      episodes={preloaded}
      isLoading={false}
      loadFailed={false}
    />
  )
}

// TODO: Validate
function GuideRow({
  channel,
  timelineMinutes,
  pixelsPerMinute,
  showChannelNumber,
  selectedEpisodeId,
  isTouchDevice,
  hideWhenEmpty,
  onHighlight,
  onMeasure,
  defaultOrder,
  episodes,
  isLoading,
  loadFailed,
}: GuideRowProps & {
  defaultOrder: Record<string, unknown>
  episodes: EpisodeWithDetails[]
  isLoading: boolean
  loadFailed: boolean
}) {
  const { user } = useAuth()
  const watchedMutation = useMarkWatched(channel.id)

  const listChannel = channel as ChannelListOutput
  const displayName = listChannel.custom_name ?? channel.name
  const displayNumber =
    listChannel.custom_channel_number ?? channel.channel_number

  const programs = scheduleEpisodes(episodes)
  const scheduledMinutes = programs.reduce(
    (total, program) => total + program.minutes,
    0,
  )

  useEffect(() => {
    onMeasure(channel.id, scheduledMinutes)
  }, [channel.id, scheduledMinutes, onMeasure])

  if (hideWhenEmpty && !isLoading && !loadFailed && programs.length === 0) {
    return null
  }

  // TODO: Validate
  const playEpisode = (episode: EpisodeWithDetails) => {
    if (user) {
      watchedMutation.mutate(episode.id)
    }
    if (episode.url) {
      window.open(episode.url, "_blank", "noopener,noreferrer")
    }
  }

  // TODO: Validate
  const highlightProgram = (program: GuideProgram) => {
    onHighlight({
      channelId: channel.id,
      channelName: displayName ?? "",
      program,
    })
  }

  // TODO: Validate
  const activateProgram = (program: GuideProgram) => {
    highlightProgram(program)
    if (isTouchDevice && selectedEpisodeId !== program.episode.id) {
      return
    }
    playEpisode(program.episode)
  }

  return (
    <div className="flex border-b last:border-b-0">
      <div className="sticky left-0 z-20 flex w-44 shrink-0 items-center gap-2 border-r bg-card px-3 py-2">
        {showChannelNumber && displayNumber != null && (
          <span className="shrink-0 text-sm text-muted-foreground tabular-nums">
            {displayNumber}
          </span>
        )}
        <Link
          to="/channels/$channelId"
          params={{ channelId: channel.id }}
          search={defaultOrder}
          className="line-clamp-2 text-sm font-semibold wrap-break-word hover:text-primary"
          title={displayName ?? undefined}
        >
          {displayName}
        </Link>
      </div>

      <div
        className="relative h-16"
        style={{ width: timelineMinutes * pixelsPerMinute }}
      >
        {isLoading &&
          Array.from({ length: 4 }).map((_, index) => (
            <Skeleton
              key={`skeleton-${channel.id}-${index}`}
              className="absolute top-1.5 bottom-1.5 rounded-sm"
              style={{
                left: index * 60 * pixelsPerMinute + 2,
                width: 60 * pixelsPerMinute - 4,
              }}
            />
          ))}

        {!isLoading && programs.length === 0 && (
          <p className="px-3 py-5 text-sm text-muted-foreground">
            {loadFailed
              ? "Could not load episodes for this channel."
              : "No episodes in this channel yet"}
          </p>
        )}

        {programs.map((program) => (
          <button
            key={program.episode.id}
            type="button"
            onClick={() => activateProgram(program)}
            onMouseEnter={
              isTouchDevice ? undefined : () => highlightProgram(program)
            }
            onFocus={
              isTouchDevice ? undefined : () => highlightProgram(program)
            }
            className={cn(
              "absolute top-1.5 bottom-1.5 overflow-hidden rounded-sm border bg-muted/40 px-2 py-1 text-left transition-colors",
              isTouchDevice
                ? "focus-visible:ring-2 focus-visible:ring-ring"
                : "hover:bg-primary hover:text-primary-foreground focus-visible:bg-primary focus-visible:text-primary-foreground",
              selectedEpisodeId === program.episode.id &&
                "border-primary bg-primary text-primary-foreground ring-2 ring-primary",
              program.episode.watch_date && "opacity-60",
            )}
            style={{
              left: program.startMinute * pixelsPerMinute + 2,
              width: program.minutes * pixelsPerMinute - 4,
            }}
            title={`${program.episode.title.name ?? ""} — ${episodeLabel(program.episode)}`}
          >
            <div className="flex min-w-0 items-center gap-1.5">
              {program.episode.source.favicon_url && (
                <Favicon
                  src={program.episode.source.favicon_url}
                  label={program.episode.source.key}
                  className="size-5"
                />
              )}
              <div className="min-w-0">
                <span className="block truncate text-sm font-medium">
                  {program.episode.title.name}
                </span>
                <span className="block truncate text-xs opacity-70">
                  {episodeLabel(program.episode)}
                </span>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

// TODO: Validate
function GuideDetail({
  selection,
  windowStart,
}: {
  selection: GuideSelection
  windowStart: Date
}) {
  const { episode } = selection.program
  const start = new Date(
    windowStart.getTime() + selection.program.startMinute * 60_000,
  )
  const end = new Date(start.getTime() + selection.program.minutes * 60_000)
  const image = episode.thumbnail_url || episode.image_url || "/no-image.svg"
  const { menuItems, dialogs } = useEpisodeActions({
    episode,
    channelId: selection.channelId,
  })

  return (
    <div className="relative flex gap-4 p-4">
      <div className="absolute top-2 right-2 z-10">
        <ResponsiveActionMenu items={menuItems} />
      </div>
      {dialogs}
      <img
        referrerPolicy="no-referrer"
        loading="lazy"
        src={image}
        alt=""
        className="hidden h-24 w-40 shrink-0 rounded-sm object-cover sm:block"
      />
      <div className="min-w-0 pr-10">
        <p className="text-lg font-semibold">{episode.title.name}</p>
        <p className="text-sm text-muted-foreground">{episodeLabel(episode)}</p>
        <p className="mt-2 text-sm text-muted-foreground">
          {slotTime(start)} - {slotTime(end)} · {selection.channelName}
          {episode.duration != null && episode.duration > 0 && (
            <> · {formatDuration(episode.duration)}</>
          )}
        </p>
        <p className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
          {episode.source.favicon_url && (
            <Favicon
              src={episode.source.favicon_url}
              label={episode.source.key}
              className="size-5"
              tooltip={false}
            />
          )}
          {episode.plugin.name ?? episode.source.key}
        </p>
      </div>
    </div>
  )
}

// TODO: Validate
export function ChannelGuide({
  rows,
  search = "",
  onSearchChange,
  isServer,
  serverRowCount,
  pagination,
  onPaginationChange,
  showChannelNumber = true,
  sortByNumber = false,
  hideEmptyChannels = false,
  showPagination = true,
  preloadedEpisodes,
}: {
  rows: BrowseChannel[]
  search?: string
  onSearchChange?: (search: string) => void
  isServer: boolean
  serverRowCount: number
  pagination: PaginationState
  onPaginationChange: (pagination: PaginationState) => void
  showChannelNumber?: boolean
  sortByNumber?: boolean
  hideEmptyChannels?: boolean
  showPagination?: boolean
  preloadedEpisodes?: Record<string, EpisodeWithDetails[]>
}) {
  const [selection, setSelection] = useState<GuideSelection | null>(null)
  const isTouchDevice = useIsTouchDevice()
  const windowStart = useMemo(guideWindowStart, [])

  const [rowMinutes, setRowMinutes] = useState<Record<string, number>>({})

  // TODO: Validate
  const measureRow = useCallback((channelId: string, minutes: number) => {
    setRowMinutes((current) =>
      current[channelId] === minutes
        ? current
        : { ...current, [channelId]: minutes },
    )
  }, [])

  // TODO: Validate
  const changeSearch = (value: string) => {
    onSearchChange?.(value)
    onPaginationChange({ ...pagination, pageIndex: 0 })
  }

  const pixelsPerMinute = 6
  const visibleRows = useMemo(() => {
    if (isServer) return rows
    const ordered = sortByNumber ? sortChannelsByNumber(rows) : rows
    const trimmed = search.trim().toLowerCase()
    if (!trimmed) return ordered
    return ordered.filter((channel) =>
      channelSearchName(channel).toLowerCase().includes(trimmed),
    )
  }, [rows, isServer, sortByNumber, search])
  usePrefetchNeighborPageEpisodes(visibleRows, pagination, !isServer)

  const pageStart = pagination.pageIndex * pagination.pageSize
  const pageRows = isServer
    ? visibleRows
    : visibleRows.slice(pageStart, pageStart + pagination.pageSize)

  const timelineMinutes =
    Math.ceil(
      Math.max(240, ...pageRows.map((channel) => rowMinutes[channel.id] ?? 0)) /
        30,
    ) * 30

  return (
    <div className="px-[4%] pb-8">
      {onSearchChange && (
        <div className="pb-4">
          <ChannelSearchInput value={search} onValueChange={changeSearch} />
        </div>
      )}

      <div className="sticky top-16 z-30 bg-background pt-2 pb-2">
        <div className="h-32 overflow-hidden rounded-md border bg-card">
          {selection ? (
            <GuideDetail selection={selection} windowStart={windowStart} />
          ) : (
            <p className="flex h-full items-center justify-center text-sm text-muted-foreground">
              {isTouchDevice
                ? "Tap a program to see its details."
                : "Hover over a program to see its details."}
            </p>
          )}
        </div>
      </div>

      <GuideTable
        windowStart={windowStart}
        timelineMinutes={timelineMinutes}
        pixelsPerMinute={pixelsPerMinute}
      >
        {pageRows.map((channel) => {
          const rowProps: GuideRowProps = {
            channel,
            timelineMinutes,
            pixelsPerMinute,
            showChannelNumber,
            selectedEpisodeId: selection?.program.episode.id ?? null,
            isTouchDevice,
            hideWhenEmpty: hideEmptyChannels,
            onHighlight: setSelection,
            onMeasure: measureRow,
          }
          const preloaded = preloadedEpisodes?.[channel.id]
          return preloaded ? (
            <PreloadedGuideRow
              key={channel.id}
              {...rowProps}
              preloaded={preloaded}
            />
          ) : (
            <FetchedGuideRow key={channel.id} {...rowProps} />
          )
        })}
      </GuideTable>

      {pageRows.length === 0 && (
        <p className="py-12 text-center text-muted-foreground">
          No channels yet. Create one to get started.
        </p>
      )}

      {showPagination && (
        <div className="sticky bottom-0 z-30 border-t border-border/50 bg-background/95 pt-2 backdrop-blur-md [&>div:last-child]:pb-3">
          <BrowsePagination
            pagination={pagination}
            onPaginationChange={onPaginationChange}
            rowCount={isServer ? serverRowCount : visibleRows.length}
          />
        </div>
      )}
    </div>
  )
}
