// TODO: Validate
import { createFileRoute } from "@tanstack/react-router"
import { OnboardingCreateName } from "@/components/Onboarding/Onboarding"

export const Route = createFileRoute("/_layout/onboarding/")({
  component: OnboardingCreateName,
})
