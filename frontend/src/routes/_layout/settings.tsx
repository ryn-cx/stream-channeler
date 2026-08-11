// TODO: Validate
import { createFileRoute } from "@tanstack/react-router"

import ChangePassword from "@/components/UserSettings/ChangePassword"
import DeleteAccount from "@/components/UserSettings/DeleteAccount"
import Preferences from "@/components/UserSettings/Preferences"
import SourcePreferences from "@/components/UserSettings/SourcePreferences"
import UserInformation from "@/components/UserSettings/UserInformation"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useAuth from "@/hooks/useAuth"

// TODO: Validate
function PreferencesTab() {
  return (
    <div className="flex flex-col gap-8">
      <Preferences />
      <SourcePreferences />
    </div>
  )
}

const tabsConfig = [
  { value: "my-profile", title: "My profile", component: UserInformation },
  { value: "preferences", title: "Preferences", component: PreferencesTab },
  { value: "password", title: "Password", component: ChangePassword },
  { value: "danger-zone", title: "Danger zone", component: DeleteAccount },
]

export const Route = createFileRoute("/_layout/settings")({
  component: UserSettings,
  head: () => ({
    meta: [
      {
        title: "Settings - Stream Channeler",
      },
    ],
  }),
})

// TODO: Validate
function UserSettings() {
  const { user: currentUser } = useAuth()
  const finalTabs = tabsConfig

  if (!currentUser) {
    return null
  }

  return (
    <div className="max-w-3xl mx-auto flex flex-col gap-6 px-4">
      <div className="text-center">
        <h1 className="text-2xl font-bold tracking-tight">User Settings</h1>
        <p className="text-muted-foreground mt-1">
          Manage your account settings and preferences
        </p>
      </div>

      <Tabs defaultValue="my-profile">
        <TabsList className="w-full justify-center">
          {finalTabs.map((tab) => (
            <TabsTrigger key={tab.value} value={tab.value}>
              {tab.title}
            </TabsTrigger>
          ))}
        </TabsList>
        {finalTabs.map((tab) => (
          <TabsContent key={tab.value} value={tab.value}>
            <tab.component />
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}
