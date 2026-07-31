// TODO: Validate
export const randomEmail = () =>
  `${Math.random().toString(36).substring(7)}@example.com`

export const randomPassword = () => `${Math.random().toString(36).substring(2)}`

export const randomUsername = (prefix: string) =>
  `${prefix} ${Math.random().toString(36).substring(7)}`
