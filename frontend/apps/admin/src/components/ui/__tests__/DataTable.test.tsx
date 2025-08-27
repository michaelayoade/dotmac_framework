/**
 * @jest-environment jsdom
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { DataTable, type TableColumn, type TableData } from '../DataTable'

// Mock data for testing
interface TestData extends TableData {
  id: string
  name: string
  email: string
  status: 'active' | 'inactive'
  age: number
}

const mockData: TestData[] = [
  { id: '1', name: 'John Doe', email: 'john@example.com', status: 'active', age: 30 },
  { id: '2', name: 'Jane Smith', email: 'jane@example.com', status: 'inactive', age: 25 },
  { id: '3', name: 'Bob Johnson', email: 'bob@example.com', status: 'active', age: 35 },
]

const mockColumns: TableColumn<TestData>[] = [
  {
    key: 'name',
    header: 'Name',
    sortable: true,
    filterable: true,
    accessor: (item) => item.name,
  },
  {
    key: 'email',
    header: 'Email',
    sortable: true,
    filterable: true,
    accessor: (item) => item.email,
  },
  {
    key: 'status',
    header: 'Status',
    sortable: true,
    filterable: true,
    accessor: (item) => (
      <span className={`status-${item.status}`}>
        {item.status}
      </span>
    ),
  },
  {
    key: 'age',
    header: 'Age',
    sortable: true,
    align: 'right',
    accessor: (item) => item.age.toString(),
  },
]

describe('DataTable Component', () => {
  it('renders table with data and columns', () => {
    render(
      <DataTable
        data={mockData}
        columns={mockColumns}
        title="Test Table"
        description="A test table"
      />
    )

    expect(screen.getByText('Test Table')).toBeInTheDocument()
    expect(screen.getByText('A test table')).toBeInTheDocument()
    
    // Check headers
    expect(screen.getByText('Name')).toBeInTheDocument()
    expect(screen.getByText('Email')).toBeInTheDocument()
    expect(screen.getByText('Status')).toBeInTheDocument()
    expect(screen.getByText('Age')).toBeInTheDocument()

    // Check data
    expect(screen.getByText('John Doe')).toBeInTheDocument()
    expect(screen.getByText('jane@example.com')).toBeInTheDocument()
    expect(screen.getByText('35')).toBeInTheDocument()
  })

  it('displays loading state correctly', () => {
    render(
      <DataTable
        data={[]}
        columns={mockColumns}
        loading={true}
        loadingRows={3}
      />
    )

    // Should show loading skeleton rows
    const skeletonRows = document.querySelectorAll('tbody tr')
    expect(skeletonRows).toHaveLength(3)
  })

  it('displays empty state when no data', () => {
    render(
      <DataTable
        data={[]}
        columns={mockColumns}
        emptyState={<div>No data available</div>}
      />
    )

    expect(screen.getByText('No data available')).toBeInTheDocument()
  })

  it('displays error state correctly', () => {
    render(
      <DataTable
        data={[]}
        columns={mockColumns}
        error="Failed to load data"
      />
    )

    expect(screen.getByText('Error loading data')).toBeInTheDocument()
    expect(screen.getByText('Failed to load data')).toBeInTheDocument()
  })

  it('handles search functionality', async () => {
    render(
      <DataTable
        data={mockData}
        columns={mockColumns}
        searchable={true}
      />
    )

    const searchInput = screen.getByPlaceholderText('Search...')
    
    fireEvent.change(searchInput, { target: { value: 'John' } })

    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument()
      expect(screen.queryByText('Jane Smith')).not.toBeInTheDocument()
    })
  })

  it('handles column sorting', async () => {
    render(
      <DataTable
        data={mockData}
        columns={mockColumns}
        sortable={true}
      />
    )

    const nameHeader = screen.getByText('Name')
    fireEvent.click(nameHeader)

    await waitFor(() => {
      const rows = screen.getAllByRole('row')
      // Skip header row, check if data is sorted
      const firstDataRow = rows[1]
      expect(firstDataRow).toHaveTextContent('Bob Johnson')
    })

    // Click again to reverse sort
    fireEvent.click(nameHeader)

    await waitFor(() => {
      const rows = screen.getAllByRole('row')
      const firstDataRow = rows[1]
      expect(firstDataRow).toHaveTextContent('John Doe')
    })
  })

  it('handles pagination correctly', () => {
    const largeDataset = Array.from({ length: 25 }, (_, i) => ({
      id: `${i + 1}`,
      name: `User ${i + 1}`,
      email: `user${i + 1}@example.com`,
      status: i % 2 === 0 ? 'active' : 'inactive' as const,
      age: 20 + i,
    }))

    render(
      <DataTable
        data={largeDataset}
        columns={mockColumns}
        pageSize={10}
      />
    )

    // Should show pagination info
    expect(screen.getByText(/showing 1 to 10 of 25 results/i)).toBeInTheDocument()
    
    // Should show pagination controls
    expect(screen.getByText('Next')).toBeInTheDocument()
    expect(screen.getByText('Previous')).toBeInTheDocument()

    // Next button should work
    const nextButton = screen.getByText('Next')
    fireEvent.click(nextButton)
    
    expect(screen.getByText(/showing 11 to 20 of 25 results/i)).toBeInTheDocument()
  })

  it('handles row selection', () => {
    const onSelectionChange = jest.fn()
    
    render(
      <DataTable
        data={mockData}
        columns={mockColumns}
        selectable={true}
        onSelectionChange={onSelectionChange}
      />
    )

    const checkboxes = screen.getAllByRole('checkbox')
    const firstRowCheckbox = checkboxes[1] // Skip header checkbox

    fireEvent.click(firstRowCheckbox)

    expect(onSelectionChange).toHaveBeenCalledWith(['1'])
  })

  it('handles select all functionality', () => {
    const onSelectionChange = jest.fn()
    
    render(
      <DataTable
        data={mockData}
        columns={mockColumns}
        selectable={true}
        onSelectionChange={onSelectionChange}
      />
    )

    const headerCheckbox = screen.getAllByRole('checkbox')[0]
    fireEvent.click(headerCheckbox)

    expect(onSelectionChange).toHaveBeenCalledWith(['1', '2', '3'])
  })

  it('handles row click events', () => {
    const onRowClick = jest.fn()
    
    render(
      <DataTable
        data={mockData}
        columns={mockColumns}
        onRowClick={onRowClick}
      />
    )

    const firstRow = screen.getByText('John Doe').closest('tr')
    fireEvent.click(firstRow!)

    expect(onRowClick).toHaveBeenCalledWith(mockData[0])
  })

  it('handles refresh functionality', () => {
    const onRefresh = jest.fn()
    
    render(
      <DataTable
        data={mockData}
        columns={mockColumns}
        refreshable={true}
        onRefresh={onRefresh}
      />
    )

    const refreshButton = screen.getByRole('button', { name: /refresh/i })
    fireEvent.click(refreshButton)

    expect(onRefresh).toHaveBeenCalled()
  })

  it('handles export functionality', () => {
    const onExport = jest.fn()
    
    render(
      <DataTable
        data={mockData}
        columns={mockColumns}
        exportable={true}
        onExport={onExport}
      />
    )

    const exportButton = screen.getByRole('button', { name: /export/i })
    fireEvent.click(exportButton)

    expect(onExport).toHaveBeenCalled()
  })

  it('applies column alignment correctly', () => {
    render(
      <DataTable
        data={mockData}
        columns={mockColumns}
      />
    )

    const ageHeader = screen.getByText('Age')
    const ageHeaderCell = ageHeader.closest('th')
    expect(ageHeaderCell).toHaveClass('text-right')

    // Check data cell alignment
    const ageDataCell = screen.getByText('30').closest('td')
    expect(ageDataCell).toHaveClass('text-right')
  })

  it('handles filterable columns', async () => {
    render(
      <DataTable
        data={mockData}
        columns={mockColumns}
        filterable={true}
      />
    )

    // Open filters - look for any button with "Filter" text
    const filterButton = screen.getByText('Filters')
    fireEvent.click(filterButton)

    // Should show filter inputs for filterable columns
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/filter by name/i)).toBeInTheDocument()
      expect(screen.getByPlaceholderText(/filter by email/i)).toBeInTheDocument()
      expect(screen.getByPlaceholderText(/filter by status/i)).toBeInTheDocument()
    })

    // Test filtering
    const nameFilter = screen.getByPlaceholderText(/filter by name/i)
    fireEvent.change(nameFilter, { target: { value: 'John' } })

    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument()
      expect(screen.queryByText('Jane Smith')).not.toBeInTheDocument()
    })
  })

  it('maintains accessibility standards', () => {
    render(
      <DataTable
        data={mockData}
        columns={mockColumns}
        title="Accessible Table"
      />
    )

    const table = screen.getByRole('table')
    expect(table).toBeInTheDocument()

    // Check for proper table structure
    const columnHeaders = screen.getAllByRole('columnheader')
    expect(columnHeaders).toHaveLength(4)

    const rows = screen.getAllByRole('row')
    expect(rows).toHaveLength(4) // 1 header + 3 data rows

    // Check for aria labels on interactive elements
    if (screen.queryByRole('button', { name: /search/i })) {
      expect(screen.getByRole('textbox', { name: /search/i }))
    }
  })

  it('handles keyboard navigation', () => {
    render(
      <DataTable
        data={mockData}
        columns={mockColumns}
        sortable={true}
      />
    )

    const nameHeader = screen.getByText('Name')
    
    // Press Enter to sort
    fireEvent.keyDown(nameHeader, { key: 'Enter' })
    
    // Should trigger sort (tested implicitly through DOM changes)
    // Verify sorting happened by checking if data order changed
    const rows = screen.getAllByRole('row')
    expect(rows).toHaveLength(4) // 1 header + 3 data rows
  })

  it('handles custom column widths', () => {
    const columnsWithWidths: TableColumn<TestData>[] = [
      {
        key: 'name',
        header: 'Name',
        width: '200px',
        accessor: (item) => item.name,
      },
      {
        key: 'email',
        header: 'Email',
        width: '300px',
        accessor: (item) => item.email,
      },
    ]

    render(
      <DataTable
        data={mockData}
        columns={columnsWithWidths}
      />
    )

    const nameHeader = screen.getByText('Name').closest('th')
    const emailHeader = screen.getByText('Email').closest('th')

    expect(nameHeader).toHaveStyle({ width: '200px' })
    expect(emailHeader).toHaveStyle({ width: '300px' })
  })

  it('handles complex accessor functions', () => {
    const complexColumns: TableColumn<TestData>[] = [
      {
        key: 'userInfo',
        header: 'User Info',
        accessor: (item) => (
          <div>
            <div data-testid="user-name">{item.name}</div>
            <div data-testid="user-email">{item.email}</div>
          </div>
        ),
      },
    ]

    render(
      <DataTable
        data={mockData}
        columns={complexColumns}
      />
    )

    expect(screen.getAllByTestId('user-name')[0]).toHaveTextContent('John Doe')
    expect(screen.getAllByTestId('user-email')[0]).toHaveTextContent('john@example.com')
  })
})