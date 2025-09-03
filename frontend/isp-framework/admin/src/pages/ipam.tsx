import { createManagementPage } from '@dotmac/patterns';
import { ipamManagementConfig } from '../config/ipam.config';

export const IPAMPage = createManagementPage(ipamManagementConfig);
export default IPAMPage;
