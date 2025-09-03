import { ManagementPageTemplate } from '@dotmac/patterns/templates';
import { projectsConfig } from '../../../config/projects.config';
import { ServiceRequestWizard } from '../../../components/projects/ServiceRequestWizard';

export default function ProjectsPage() {
  return (
    <ManagementPageTemplate config={projectsConfig}>
      <ServiceRequestWizard />
    </ManagementPageTemplate>
  );
}
