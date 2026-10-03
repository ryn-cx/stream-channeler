// TODO: Validate
export const randomEmail = () =>
  `${Math.random().toString(36).substring(7)}@example.com`

// TODO: Validate
export const randomPassword = () => `${Math.random().toString(36).substring(2)}`

// TODO: Validate
export const randomUsername = (prefix: string) =>
  `${prefix} ${Math.random().toString(36).substring(7)}`
