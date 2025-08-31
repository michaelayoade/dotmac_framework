import { DashboardTemplate } from '@dotmac/patterns/templates';
import { qualityConfig } from '../../../config/quality.config';

export default function QualityPage() {
  return <DashboardTemplate config={qualityConfig} />;
}
