import { ManagementPageTemplate } from '@dotmac/patterns/templates';
import { ticketsConfig } from '../../../../config/tickets.config';
import { ConversationPanel } from '../../../../components/support/ConversationPanel';

export default function TicketsPage() {
  return (
    <ManagementPageTemplate config={ticketsConfig}>
      <ConversationPanel />
    </ManagementPageTemplate>
  );
}
