// TODO: Validate
import { VideoStoreService } from "@/client"

// TODO: Validate
export const fetchTitleDetail = (titleId: string) =>
  VideoStoreService.getTitleDetail({ titleId })
