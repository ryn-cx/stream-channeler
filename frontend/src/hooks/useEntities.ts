// TODO: Validate
import { useQuery } from "@tanstack/react-query"

import {
  EpisodesService,
  PluginsService,
  SeasonsService,
  SourcesService,
  TitlesService,
} from "@/client"

// TODO: Validate
export function usePlugin(pluginId: string | undefined) {
  return useQuery({
    queryKey: ["plugins", pluginId],
    queryFn: () => PluginsService.getPlugin({ pluginId: pluginId! }),
    enabled: !!pluginId,
  })
}

// TODO: Validate
export function useSource(sourceId: string | undefined) {
  return useQuery({
    queryKey: ["sources", sourceId],
    queryFn: () => SourcesService.getSource({ sourceId: sourceId! }),
    enabled: !!sourceId,
  })
}

// TODO: Validate
export function useTitle(titleId: string | undefined) {
  return useQuery({
    queryKey: ["titles", titleId],
    queryFn: () => TitlesService.getTitle({ titleId: titleId! }),
    enabled: !!titleId,
  })
}

// TODO: Validate
export function useSeason(seasonId: string | undefined) {
  return useQuery({
    queryKey: ["seasons", seasonId],
    queryFn: () => SeasonsService.getSeason({ seasonId: seasonId! }),
    enabled: !!seasonId,
  })
}

// TODO: Validate
export function useEpisode(episodeId: string | undefined) {
  return useQuery({
    queryKey: ["episodes", episodeId],
    queryFn: () => EpisodesService.getEpisode({ episodeId: episodeId! }),
    enabled: !!episodeId,
  })
}

// TODO: Validate
export function useSearchablePlugins(enabled = true) {
  return useQuery({
    queryKey: ["searchable-plugins"],
    queryFn: () => PluginsService.searchInformation(),
    enabled,
  })
}
