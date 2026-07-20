type AvatarPalette = {
  bg: string
  fg: string
  accent: string
  soft: string
}

export type BuiltInUserAvatar = {
  id: string
  name: string
  src: string
}

export type AvatarSeedUser = {
  id?: string | number | null
  username?: string | null
}

export const USER_AVATAR_STORAGE_KEY = 'zhido:user-avatar-id'

const palettes: AvatarPalette[] = [
  { bg: '#153c2c', fg: '#f7fff9', accent: '#bee83f', soft: '#3bb36b' },
  { bg: '#17324d', fg: '#f6fbff', accent: '#79c7ff', soft: '#4d8fd7' },
  { bg: '#43234d', fg: '#fff8ff', accent: '#ffcb6b', soft: '#c47bd6' },
  { bg: '#4a3020', fg: '#fffaf5', accent: '#8ee6c8', soft: '#d58b58' },
  { bg: '#202733', fg: '#f8fbff', accent: '#ff7aa8', soft: '#7f98c6' },
]

const hashString = (value: string) => {
  let hash = 0
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash << 5) - hash + value.charCodeAt(index)
    hash |= 0
  }
  return Math.abs(hash)
}

const svgDataUri = (svg: string) => {
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`
}

export const getAvatarInitial = (value?: string, fallback = 'U') => {
  const trimmed = String(value || '').trim()
  return trimmed.slice(0, 1).toUpperCase() || fallback
}

export const isImageAvatar = (avatar?: string) => {
  const value = String(avatar || '').trim()
  return (
    value.startsWith('data:image/') ||
    value.startsWith('/uploads/') ||
    value.startsWith('http://') ||
    value.startsWith('https://')
  )
}

export const generatePersonaAvatar = (name?: string, title?: string, seedExtra?: string) => {
  const seed = `${name || 'agent'}|${title || ''}|${seedExtra || ''}`
  const hash = hashString(seed)
  const palette = palettes[hash % palettes.length]
  const initial = getAvatarInitial(name, '智')
  const orbit = 34 + (hash % 18)
  const corner = 18 + (hash % 16)
  const slash = 18 + (hash % 28)

  return svgDataUri(`
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" role="img" aria-label="${initial} avatar">
      <defs>
        <linearGradient id="bg" x1="18" y1="12" x2="112" y2="120" gradientUnits="userSpaceOnUse">
          <stop stop-color="${palette.bg}"/>
          <stop offset="1" stop-color="${palette.soft}"/>
        </linearGradient>
        <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="8" stdDeviation="8" flood-color="#000000" flood-opacity="0.22"/>
        </filter>
      </defs>
      <rect width="128" height="128" rx="30" fill="url(#bg)"/>
      <circle cx="104" cy="24" r="${corner}" fill="${palette.accent}" opacity="0.28"/>
      <circle cx="28" cy="106" r="${orbit}" fill="#ffffff" opacity="0.12"/>
      <path d="M18 ${96 - slash} C42 ${28 + slash}, 72 ${112 - slash}, 112 ${36 + slash}" fill="none" stroke="${palette.accent}" stroke-width="8" stroke-linecap="round" opacity="0.72"/>
      <rect x="26" y="28" width="76" height="76" rx="24" fill="rgba(255,255,255,0.16)" filter="url(#shadow)"/>
      <text x="64" y="77" text-anchor="middle" font-family="system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="42" font-weight="800" fill="${palette.fg}">${initial}</text>
    </svg>
  `)
}

export const builtInUserAvatars: BuiltInUserAvatar[] = [
  {
    id: 'bamboo',
    name: '青竹',
    src: generatePersonaAvatar('竹', 'user', 'bamboo')
  },
  {
    id: 'orbit',
    name: '星轨',
    src: generatePersonaAvatar('星', 'user', 'orbit')
  },
  {
    id: 'ember',
    name: '微光',
    src: generatePersonaAvatar('光', 'user', 'ember')
  },
  {
    id: 'harbor',
    name: '港湾',
    src: generatePersonaAvatar('渡', 'user', 'harbor')
  }
]

export const pickBuiltInUserAvatar = (seed?: string | number) => {
  const index = hashString(String(seed ?? 'user')) % builtInUserAvatars.length
  return builtInUserAvatars[index]
}

export const resolveBuiltInUserAvatar = (user?: AvatarSeedUser | null, storedAvatarId?: string | null) => {
  const selectedId = storedAvatarId ?? (
    typeof localStorage === 'undefined' ? '' : localStorage.getItem(USER_AVATAR_STORAGE_KEY)
  )
  return (
    builtInUserAvatars.find(avatar => avatar.id === selectedId) ||
    pickBuiltInUserAvatar(user?.id || user?.username || 'user')
  )
}

export const resolveBuiltInUserAvatarSrc = (user?: AvatarSeedUser | null, storedAvatarId?: string | null) => {
  return resolveBuiltInUserAvatar(user, storedAvatarId).src
}
