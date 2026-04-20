// TODO: Validate
import { Link } from "@tanstack/react-router"
import { Check, Play, Tv, Users, X, Zap } from "lucide-react"

import type { SortKeyInput } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import useAuth from "@/hooks/useAuth"

const DEMO_CHANNEL_ID = "3d174ad5-41ed-4110-8ef1-5e7f1653f9d5"

const DEMO_SORT_BY: SortKeyInput[] = [
  {
    model: "season",
    field: "sequential",
    direction: "ascending",
    order: "sequential",
  },
  {
    model: "episode",
    field: "sequential",
    direction: "ascending",
    order: "sequential",
  },
  {
    model: "episode",
    field: "id",
    direction: "ascending",
    order: "randomize",
  },
]

export function InfoPage() {
  const { user } = useAuth()
  const getStartedTo = user ? "/dashboard" : "/signup"

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      {/* Hero Section */}
      <div className="container mx-auto px-4 py-16 md:py-24">
        <div className="text-center max-w-4xl mx-auto">
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight mb-6">
            Your Personal TV Channels,
            <span className="text-primary block">
              Completely Under Your Control
            </span>
          </h1>
          <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
            Media center software for the streaming era. Create unlimited TV
            channels, choose exactly what each channel should contain, and watch
            on your schedule.
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <Button asChild size="lg">
              <Link
                to="/channels/$channelId"
                params={{ channelId: DEMO_CHANNEL_ID }}
                search={{ sortBy: DEMO_SORT_BY }}
              >
                <Tv className="mr-2" />
                View Demo Channel
              </Link>
            </Button>
            <Button asChild size="lg">
              <Link to={getStartedTo}>
                <Users className="mr-2" />
                Sign Up
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link to="/login">Sign In</Link>
            </Button>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="container mx-auto px-4 py-16">
        <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="rounded-full bg-primary/10 w-12 h-12 flex items-center justify-center shrink-0">
                <Tv className="text-primary" />
              </div>
              <h3 className="text-xl font-semibold">Unlimited Channels</h3>
            </div>
            <p className="text-muted-foreground">
              Create as many custom TV channels as you want. Each channel can
              have its own unique content and playback order.
            </p>
          </Card>

          <Card className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="rounded-full bg-primary/10 w-12 h-12 flex items-center justify-center shrink-0">
                <Play className="text-primary" />
              </div>
              <h3 className="text-xl font-semibold">Watch Your Way</h3>
            </div>
            <p className="text-muted-foreground">
              Channels only air when you want them to. No more missing your
              favorite shows or waiting for specific air times.
            </p>
          </Card>

          <Card className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="rounded-full bg-primary/10 w-12 h-12 flex items-center justify-center shrink-0">
                <Zap className="text-primary" />
              </div>
              <h3 className="text-xl font-semibold">Hundreds of Sources</h3>
            </div>
            <p className="text-muted-foreground">
              Supported through a flexible plugin architecture. Anyone can
              create plugins to support additional media sources.
            </p>
          </Card>
        </div>
      </div>

      {/* How It Works Section */}
      <div className="container mx-auto px-4 py-16 bg-muted/30">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-12">How It Works</h2>
          <div className="space-y-8">
            <div className="flex gap-6 items-start">
              <div className="rounded-full bg-primary text-primary-foreground w-10 h-10 flex items-center justify-center font-bold shrink-0">
                1
              </div>
              <div>
                <h3 className="text-xl font-semibold mb-2">
                  Create Your Channels
                </h3>
                <p className="text-muted-foreground">
                  Set up custom TV channels and give them meaningful names that
                  reflect their content.
                </p>
              </div>
            </div>

            <div className="flex gap-6 items-start">
              <div className="rounded-full bg-primary text-primary-foreground w-10 h-10 flex items-center justify-center font-bold shrink-0">
                2
              </div>
              <div>
                <h3 className="text-xl font-semibold mb-2">Add Your Content</h3>
                <p className="text-muted-foreground">
                  Choose exactly what media each channel should contain from
                  hundreds of supported streaming sources.
                </p>
              </div>
            </div>

            <div className="flex gap-6 items-start">
              <div className="rounded-full bg-primary text-primary-foreground w-10 h-10 flex items-center justify-center font-bold shrink-0">
                3
              </div>
              <div>
                <h3 className="text-xl font-semibold mb-2">
                  Customize Playback
                </h3>
                <p className="text-muted-foreground">
                  Set parameters to control playback order, rotation, filters,
                  and more to create the perfect viewing experience.
                </p>
              </div>
            </div>

            <div className="flex gap-6 items-start">
              <div className="rounded-full bg-primary text-primary-foreground w-10 h-10 flex items-center justify-center font-bold shrink-0">
                4
              </div>
              <div>
                <h3 className="text-xl font-semibold mb-2">Start Watching</h3>
                <p className="text-muted-foreground">
                  Tune into your channels and enjoy content just like
                  traditional TV, but completely on your terms.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Pricing Section */}
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-4">Ready to Get Started?</h2>
            <p className="text-muted-foreground">
              Choose the plan that works for you.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            {/* Free Plan */}
            <Card className="p-6 flex flex-col">
              <div className="mb-6">
                <h3 className="text-2xl font-bold">Free</h3>
                <div className="mt-2">
                  <span className="text-4xl font-bold">$0</span>
                  <span className="text-muted-foreground"> / month</span>
                </div>
              </div>
              <ul className="space-y-3 mb-8 flex-1">
                <li className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-primary shrink-0" />
                  <span>Up to 10 channels</span>
                </li>
                <li className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-primary shrink-0" />
                  <span>Up to 20 shows per channel</span>
                </li>
                <li className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-primary shrink-0" />
                  <span>Up to 5 shared channels</span>
                </li>
                <li className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-primary shrink-0" />
                  <span>Watch history kept for 365 days</span>
                </li>
                <li className="flex items-center gap-2">
                  <X className="h-4 w-4 text-destructive shrink-0" />
                  <span className="text-muted-foreground">
                    Manual watch history only
                  </span>
                </li>
                <li className="flex items-center gap-2">
                  <X className="h-4 w-4 text-destructive shrink-0" />
                  <span className="text-muted-foreground">Website only</span>
                </li>
              </ul>
              <Button asChild size="lg" variant="outline" className="w-full">
                <Link to={getStartedTo}>Get Started</Link>
              </Button>
            </Card>

            {/* Premium Plan */}
            <Card className="p-6 flex flex-col border-primary relative">
              <Badge className="absolute -top-3 left-1/2 -translate-x-1/2">
                Recommended
              </Badge>
              <div className="mb-6">
                <h3 className="text-2xl font-bold">Premium</h3>
                <div className="mt-2">
                  <span className="text-4xl font-bold">$5</span>
                  <span className="text-muted-foreground"> / month</span>
                </div>
              </div>
              <ul className="space-y-3 mb-8 flex-1">
                <li className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-primary shrink-0" />
                  <span>Unlimited channels</span>
                </li>
                <li className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-primary shrink-0" />
                  <span>Unlimited shows per channel</span>
                </li>
                <li className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-primary shrink-0" />
                  <span>Unlimited shared channels</span>
                </li>
                <li className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-primary shrink-0" />
                  <span>Unlimited watch history</span>
                </li>
                <li className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-primary shrink-0" />
                  <span>Import watch history from other sources</span>
                </li>
                <li className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-primary shrink-0" />
                  <span>Desktop & mobile app</span>
                </li>
                <li className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-primary shrink-0" />
                  <span>AI Powered Channel Builder</span>
                  <Badge variant="secondary" className="text-xs">
                    Coming Soon
                  </Badge>
                </li>
              </ul>
              <Button asChild size="lg" className="w-full">
                <Link to="/signup">Start Free Trial</Link>
              </Button>
              <p className="text-xs text-muted-foreground text-center mt-3">
                No credit card required. All new accounts include a free trial
                of Premium.
              </p>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}
