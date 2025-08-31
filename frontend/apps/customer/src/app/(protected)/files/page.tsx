import { ManagementPageTemplate } from '@dotmac/patterns/templates';
import { filesConfig } from '../../../config/files.config';
import { UploadArea } from '../../../components/files/UploadArea';
import { FilesDataTable } from '../../../components/files/FilesDataTable';

export default function FilesPage() {
  return (
    <ManagementPageTemplate config={filesConfig}>
      <UploadArea />
      <FilesDataTable />
    </ManagementPageTemplate>
  );
}
