import type { CapacitorConfig } from '@capacitor/cli'
import branding from '../others/config/branding.json'

const config: CapacitorConfig = {
  appId: 'cn.labconnect.platform', appName: branding.brandName, webDir: '../web/dist',
  server: { androidScheme: 'https', cleartext: false },
  android: { path: 'native', allowMixedContent: false },
}
export default config
