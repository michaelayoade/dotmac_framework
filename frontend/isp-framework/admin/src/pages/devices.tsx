import { createManagementPage } from '@dotmac/patterns';
import { deviceManagementConfig } from '../config/devices.config';

export const DevicesPage = createManagementPage(deviceManagementConfig);
export default DevicesPage;
