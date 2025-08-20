# DotMac Platform Go SDK

Official Go SDK for the DotMac Platform API.

## Installation

```bash
go get github.com/dotmac/platform-sdk-go
```

## Quick Start

```go
package main

import (
    "fmt"
    "log"
    "github.com/dotmac/platform-sdk-go"
)

func main() {
    // Initialize client with API key
    client := dotmac.NewClient(dotmac.Config{
        BaseURL: "https://api.dotmac.com",
        APIKey:  "your-api-key",
    })

    // Create a customer
    customer, err := client.Customers.Create(dotmac.CreateCustomerRequest{
        DisplayName:  "Acme Corp",
        CustomerType: "business",
        PrimaryEmail: "contact@acme.com",
        PrimaryPhone: "+1-555-0123",
    })
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Created customer: %s\n", customer.ID)

    // List customers
    customers, err := client.Customers.List(1, 20)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Found %d customers\n", customers.Total)

    // Create a support ticket
    ticket, err := client.Tickets.Create(dotmac.CreateTicketRequest{
        CustomerID:  customer.ID,
        Subject:     "Internet connection issue",
        Description: "Connection drops every hour",
        Priority:    "high",
    })
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Created ticket: %s\n", ticket.ID)
}
```

## Documentation

Full documentation: https://docs.dotmac.com/sdk/go

## License

MIT License
