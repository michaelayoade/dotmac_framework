import { createManagementPage } from '@dotmac/patterns';
import { containerManagementConfig } from '../config/containers.config';

export const ContainersPage = createManagementPage(containerManagementConfig);
export default ContainersPage;
