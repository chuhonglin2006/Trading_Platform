// 全部使用线条 SVG 图标，不使用任何表情符号（emoji）

export const CATEGORY_ICON_PATHS = {
  book: '<path d="M4 5.5C4 4.7 4.7 4 5.5 4H12v16H5.5c-.8 0-1.5-.7-1.5-1.5v-13Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M20 5.5c0-.8-.7-1.5-1.5-1.5H12v16h6.5c.8 0 1.5-.7 1.5-1.5v-13Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>',
  digital: '<rect x="3.5" y="5" width="17" height="11" rx="1.2" stroke="currentColor" stroke-width="1.5"/><path d="M2 19h20" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>',
  clothes: '<path d="M9 4 12 6l3-2 4 3-2 3-2-1v11H9V9L7 10l-2-3 4-3Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>',
  life: '<path d="M10 3h4v2.4l2 2.6v11a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2V8l2-2.6V3Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M8.5 12h7" stroke="currentColor" stroke-width="1.5"/>',
  sport: '<circle cx="12" cy="12" r="8.5" stroke="currentColor" stroke-width="1.5"/><path d="M12 3.5v17M3.7 8.7h16.6M3.7 15.3h16.6" stroke="currentColor" stroke-width="1.5"/>',
  furniture: '<path d="M5 12V7a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M4 12h16v4a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-4Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M5 17v2M19 17v2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>',
  other: '<rect x="4" y="4" width="16" height="16" rx="2" stroke="currentColor" stroke-width="1.5"/><path d="M4 9.5h16" stroke="currentColor" stroke-width="1.5"/>',
}

export const ICON_SEARCH = '<circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="1.6"/><path d="M21 21l-4.3-4.3" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>'
export const ICON_HEART = '<path d="M12 20.5s-7.5-4.6-9.7-9C.7 8 2 4.7 5.3 4c2.1-.4 4 .5 5.2 2.2C11.7 4.5 13.6 3.6 15.7 4 19 4.7 20.3 8 18.7 11.5c-2.2 4.4-6.7 9-6.7 9Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>'
export const ICON_SUN = '<circle cx="12" cy="12" r="4.2" stroke="currentColor" stroke-width="1.6"/><path d="M12 2.5v2.4M12 19.1v2.4M4.2 4.2l1.7 1.7M18.1 18.1l1.7 1.7M2.5 12h2.4M19.1 12h2.4M4.2 19.8l1.7-1.7M18.1 5.9l1.7-1.7" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>'
export const ICON_MOON = '<path d="M20.5 14.7A8.5 8.5 0 1 1 9.3 3.5a7 7 0 0 0 11.2 11.2Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>'
export const ICON_BOX = '<path d="M3.5 8 12 4l8.5 4L12 12 3.5 8Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M3.5 8v8L12 20V12M20.5 8v8L12 20" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>'
export const ICON_RECEIPT = '<path d="M6 3h12v18l-2.5-1.6L13 21l-2.5-1.6L8 21l-2-1.6V3Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M9 8h6M9 12h6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>'
export const ICON_HOME = '<path d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-4.5v-6h-5v6H5a1 1 0 0 1-1-1v-9.5Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>'
export const ICON_USER = '<circle cx="12" cy="8.2" r="3.4" stroke="currentColor" stroke-width="1.5"/><path d="M4.5 20c1-3.6 4.2-5.6 7.5-5.6s6.5 2 7.5 5.6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>'
export const ICON_FLAG = '<path d="M6 3v18" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M6 4h11l-2.5 4L17 12H6" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>'

export const CATEGORIES = [
  { key: 'book', label: '教材书籍' },
  { key: 'digital', label: '数码电子' },
  { key: 'clothes', label: '服装配饰' },
  { key: 'life', label: '生活日用' },
  { key: 'sport', label: '运动户外' },
  { key: 'furniture', label: '家具家电' },
  { key: 'other', label: '其他' },
]

export function catInfo(key) {
  return CATEGORIES.find((c) => c.key === key) || CATEGORIES[CATEGORIES.length - 1]
}

export function catIconPath(key) {
  return CATEGORY_ICON_PATHS[key] || CATEGORY_ICON_PATHS.other
}
