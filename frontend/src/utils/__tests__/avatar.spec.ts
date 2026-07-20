import { describe, expect, it } from 'vitest'
import {
  builtInUserAvatars,
  generatePersonaAvatar,
  getAvatarInitial,
  isImageAvatar
} from '../avatar'

describe('avatar utilities', () => {
  it('generates deterministic image avatars for personas', () => {
    const avatar = generatePersonaAvatar('苏格拉底', '古希腊哲学家', '追问真理')

    expect(avatar).toMatch(/^data:image\/svg\+xml;charset=UTF-8,/)
    expect(isImageAvatar(avatar)).toBe(true)
    expect(generatePersonaAvatar('苏格拉底', '古希腊哲学家', '追问真理')).toBe(avatar)
  })

  it('provides built-in user avatar images instead of relying only on initials', () => {
    expect(builtInUserAvatars.length).toBeGreaterThanOrEqual(4)
    expect(builtInUserAvatars[0].src).toMatch(/^data:image\/svg\+xml;charset=UTF-8,/)
  })

  it('keeps a readable initial fallback', () => {
    expect(getAvatarInitial('Alice')).toBe('A')
    expect(getAvatarInitial('张三')).toBe('张')
    expect(getAvatarInitial('')).toBe('U')
  })
})
