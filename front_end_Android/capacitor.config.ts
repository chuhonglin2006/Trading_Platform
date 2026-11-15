import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'com.chuhl.campusmarket',
  appName: '校园二手交易平台',
  webDir: 'dist',
  backgroundColor: '#ffffff',
  android: {
    backgroundColor: '#ffffff',
    zoomEnabled: false,
  },
}

export default config
