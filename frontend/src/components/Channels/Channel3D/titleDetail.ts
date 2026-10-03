// TODO: Validate
import { VideoStoreService } from "@/client"

// TODO: Validate
export const fetchTitleDetail = (
  titleId: string,
  metadata: "tmdb" | "source",
) => VideoStoreService.getTitleDetail({ titleId, metadata })
