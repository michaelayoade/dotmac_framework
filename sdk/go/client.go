package dotmac

import (
    "fmt"
    "time"
    "github.com/go-resty/resty/v2"
)

// Config represents the SDK configuration
type Config struct {
    BaseURL     string
    APIKey      string
    AccessToken string
    Timeout     time.Duration
}

// Client is the main DotMac API client
type Client struct {
    config    Config
    http      *resty.Client
    Customers *CustomerService
    Tickets   *TicketService
    Invoices  *InvoiceService
}

// NewClient creates a new DotMac API client
func NewClient(config Config) *Client {
    if config.BaseURL == "" {
        config.BaseURL = "https://api.dotmac.com"
    }
    if config.Timeout == 0 {
        config.Timeout = 30 * time.Second
    }

    httpClient := resty.New().
        SetBaseURL(config.BaseURL).
        SetTimeout(config.Timeout).
        SetHeader("Content-Type", "application/json")

    if config.APIKey != "" {
        httpClient.SetHeader("X-API-Key", config.APIKey)
    } else if config.AccessToken != "" {
        httpClient.SetHeader("Authorization", "Bearer "+config.AccessToken)
    }

    client := &Client{
        config: config,
        http:   httpClient,
    }

    // Initialize services
    client.Customers = &CustomerService{client: client}
    client.Tickets = &TicketService{client: client}
    client.Invoices = &InvoiceService{client: client}

    return client
}

// Customer represents a customer entity
type Customer struct {
    ID             string    `json:"id"`
    CustomerNumber string    `json:"customer_number"`
    DisplayName    string    `json:"display_name"`
    CustomerType   string    `json:"customer_type"`
    State          string    `json:"state"`
    CreatedAt      time.Time `json:"created_at"`
    UpdatedAt      time.Time `json:"updated_at"`
}

// CreateCustomerRequest represents the request to create a customer
type CreateCustomerRequest struct {
    DisplayName    string                 `json:"display_name"`
    CustomerType   string                 `json:"customer_type"`
    PrimaryEmail   string                 `json:"primary_email"`
    PrimaryPhone   string                 `json:"primary_phone"`
    ServiceAddress map[string]interface{} `json:"service_address,omitempty"`
}

// PaginatedResponse represents a paginated API response
type PaginatedResponse[T any] struct {
    Items   []T  `json:"items"`
    Total   int  `json:"total"`
    Page    int  `json:"page"`
    Limit   int  `json:"limit"`
    Pages   int  `json:"pages"`
    HasNext bool `json:"has_next"`
    HasPrev bool `json:"has_prev"`
}

// CustomerService handles customer-related operations
type CustomerService struct {
    client *Client
}

// Create creates a new customer
func (s *CustomerService) Create(req CreateCustomerRequest) (*Customer, error) {
    var customer Customer
    _, err := s.client.http.R().
        SetBody(req).
        SetResult(&customer).
        Post("/api/v1/customers")
    return &customer, err
}

// Get retrieves a customer by ID
func (s *CustomerService) Get(customerID string) (*Customer, error) {
    var customer Customer
    _, err := s.client.http.R().
        SetResult(&customer).
        Get(fmt.Sprintf("/api/v1/customers/%s", customerID))
    return &customer, err
}

// List retrieves a paginated list of customers
func (s *CustomerService) List(page, limit int) (*PaginatedResponse[Customer], error) {
    var response PaginatedResponse[Customer]
    _, err := s.client.http.R().
        SetQueryParam("page", fmt.Sprintf("%d", page)).
        SetQueryParam("limit", fmt.Sprintf("%d", limit)).
        SetResult(&response).
        Get("/api/v1/customers")
    return &response, err
}

// TicketService handles ticket-related operations
type TicketService struct {
    client *Client
}

// Ticket represents a support ticket
type Ticket struct {
    ID         string    `json:"id"`
    CustomerID string    `json:"customer_id"`
    Subject    string    `json:"subject"`
    Status     string    `json:"status"`
    Priority   string    `json:"priority"`
    CreatedAt  time.Time `json:"created_at"`
    UpdatedAt  time.Time `json:"updated_at"`
}

// CreateTicketRequest represents the request to create a ticket
type CreateTicketRequest struct {
    CustomerID  string `json:"customer_id"`
    Subject     string `json:"subject"`
    Description string `json:"description"`
    Priority    string `json:"priority,omitempty"`
}

// Create creates a new support ticket
func (s *TicketService) Create(req CreateTicketRequest) (*Ticket, error) {
    var ticket Ticket
    _, err := s.client.http.R().
        SetBody(req).
        SetResult(&ticket).
        Post("/api/v1/tickets")
    return &ticket, err
}

// InvoiceService handles invoice-related operations
type InvoiceService struct {
    client *Client
}

// Invoice represents an invoice
type Invoice struct {
    ID         string    `json:"id"`
    CustomerID string    `json:"customer_id"`
    Amount     float64   `json:"amount"`
    Currency   string    `json:"currency"`
    Status     string    `json:"status"`
    DueDate    string    `json:"due_date"`
    CreatedAt  time.Time `json:"created_at"`
}

// List retrieves a paginated list of invoices
func (s *InvoiceService) List(customerID string) (*PaginatedResponse[Invoice], error) {
    var response PaginatedResponse[Invoice]
    req := s.client.http.R().SetResult(&response)
    
    if customerID != "" {
        req.SetQueryParam("customer_id", customerID)
    }
    
    _, err := req.Get("/api/v1/invoices")
    return &response, err
}
