import { useQuery } from "@tanstack/react-query"

import {
  PluginsService,
  SeasonsService,
  ShowsService,
  SourcesService,
} from "@/client"

export function usePlugin(pluginId: string | undefined) {
  return useQuery({
    queryKey: ["plugins", pluginId],
    queryFn: () => PluginsService.getPlugin({ pluginId: pluginId! }),
    enabled: !!pluginId,
  })
}

export function useSource(sourceId: string | undefined) {
  return useQuery({
    queryKey: ["sources", sourceId],
    queryFn: () => SourcesService.getSource({ sourceId: sourceId! }),
    enabled: !!sourceId,
  })
}

export function useShow(showId: string | undefined) {
  return useQuery({
    queryKey: ["shows", showId],
    queryFn: () => ShowsService.getShow({ showId: showId! }),
    enabled: !!showId,
  })
}

export function useSeason(seasonId: string | undefined) {
  return useQuery({
    queryKey: ["seasons", seasonId],
    queryFn: () => SeasonsService.getSeason({ seasonId: seasonId! }),
    enabled: !!seasonId,
  })
}
