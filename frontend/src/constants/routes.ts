
export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  MEMBERS: '/members',
  MEMBERS_ADD: '/members/add',
  MEMBERS_DETAIL: (id: number) => `/members/${id}`,
  MEMBERS_EDIT: (id: number) => `/members/${id}/edit`,
  SETTINGS: '/settings',
};