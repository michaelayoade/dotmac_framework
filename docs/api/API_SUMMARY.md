# DotMac Platform API Endpoints
Generated: 2025-08-19T22:53:34.655283

## Api Gateway

| Method | Path | Description | Operation ID |
|--------|------|-------------|-------------|
| GET | `/api_gateway` | Root | root__get |
| GET | `/api_gateway/api/v1/customers` | List Customers | list_customers_api_v1_customers_get |
| POST | `/api_gateway/api/v1/customers` | Create Customer | create_customer_api_v1_customers_post |
| DELETE | `/api_gateway/api/v1/customers/{customer_id}` | Delete Customer | delete_customer_api_v1_customers__customer_id__delete |
| GET | `/api_gateway/api/v1/customers/{customer_id}` | Get Customer | get_customer_api_v1_customers__customer_id__get |
| PUT | `/api_gateway/api/v1/customers/{customer_id}` | Update Customer | update_customer_api_v1_customers__customer_id__put |
| POST | `/api_gateway/api/v1/customers/{customer_id}/reactivate` | Reactivate Customer | reactivate_customer_api_v1_customers__customer_id__reactivate_post |
| GET | `/api_gateway/api/v1/customers/{customer_id}/services` | Get Customer Services | get_customer_services_api_v1_customers__customer_id__services_get |
| POST | `/api_gateway/api/v1/customers/{customer_id}/suspend` | Suspend Customer | suspend_customer_api_v1_customers__customer_id__suspend_post |
| GET | `/api_gateway/api/v1/invoices` | List Invoices | list_invoices_api_v1_invoices_get |
| GET | `/api_gateway/api/v1/network/devices` | List Network Devices | list_network_devices_api_v1_network_devices_get |
| GET | `/api_gateway/api/v1/network/status` | Get Network Status | get_network_status_api_v1_network_status_get |
| GET | `/api_gateway/api/v1/openapi` | Get Openapi Spec | get_openapi_spec_api_v1_openapi_get |
| POST | `/api_gateway/api/v1/payments` | Process Payment | process_payment_api_v1_payments_post |
| GET | `/api_gateway/api/v1/services` | List Services | list_services_api_v1_services_get |
| GET | `/api_gateway/api/v1/stats` | Get Api Stats | get_api_stats_api_v1_stats_get |
| GET | `/api_gateway/api/v1/tickets` | List Tickets | list_tickets_api_v1_tickets_get |
| POST | `/api_gateway/api/v1/tickets` | Create Ticket | create_ticket_api_v1_tickets_post |
| GET | `/api_gateway/api/v1/tickets/sla-status` | Get Sla Status | get_sla_status_api_v1_tickets_sla_status_get |
| GET | `/api_gateway/api/v1/tickets/{ticket_id}` | Get Ticket Details | get_ticket_details_api_v1_tickets__ticket_id__get |
| PUT | `/api_gateway/api/v1/tickets/{ticket_id}` | Update Ticket | update_ticket_api_v1_tickets__ticket_id__put |
| POST | `/api_gateway/api/v1/tickets/{ticket_id}/assign` | Assign Ticket | assign_ticket_api_v1_tickets__ticket_id__assign_post |
| POST | `/api_gateway/api/v1/tickets/{ticket_id}/close` | Close Ticket | close_ticket_api_v1_tickets__ticket_id__close_post |
| POST | `/api_gateway/api/v1/tickets/{ticket_id}/comments` | Add Ticket Comment | add_ticket_comment_api_v1_tickets__ticket_id__comments_post |
| POST | `/api_gateway/api/v1/tickets/{ticket_id}/escalate` | Escalate Ticket | escalate_ticket_api_v1_tickets__ticket_id__escalate_post |
| GET | `/api_gateway/api/v1/tickets/{ticket_id}/history` | Get Ticket History | get_ticket_history_api_v1_tickets__ticket_id__history_get |
| POST | `/api_gateway/api/v1/tickets/{ticket_id}/reopen` | Reopen Ticket | reopen_ticket_api_v1_tickets__ticket_id__reopen_post |
| GET | `/api_gateway/health` | Health Check | health_check_health_get |

## Statistics

- Total Services: 1
- Total Endpoints: 23
- Total Schemas: 15
