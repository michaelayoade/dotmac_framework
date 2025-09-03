import { createManagementPage } from '@dotmac/patterns';
import { projectManagementConfig } from '../config/projects.config';

export const ProjectsPage = createManagementPage(projectManagementConfig);
export default ProjectsPage;
