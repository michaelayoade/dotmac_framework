import { BusinessRulesManager } from '../../components/business-rules';

export default function BusinessRulesPage() {
  return (
    <div className='container mx-auto px-4 py-6'>
      <BusinessRulesManager />
    </div>
  );
}

export const metadata = {
  title: 'Business Rules - Admin Portal',
  description: 'Manage automated business logic and decision-making rules',
};
