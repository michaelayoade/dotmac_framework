'use client';

import React, { useState, useEffect } from 'react';
import { ManagementPageTemplate } from '@dotmac/primitives/templates/ManagementPageTemplate';
import { PlusIcon, QrCodeIcon, SignalIcon, SignalSlashIcon } from '@heroicons/react/24/outline';
import { useOfflineSync } from '@/hooks/useOfflineSync';

interface InventoryItem {
  id: string;
  type: 'modem' | 'router' | 'cable' | 'splitter' | 'other';
  model: string;
  serial: string;
  status: 'available' | 'assigned' | 'installed' | 'defective' | 'returned';
  location: string;
  assignedTo?: string;
  installationDate?: string;
  notes?: string;
  lastUpdated: string;
  syncStatus: 'synced' | 'pending' | 'failed';
}

const mockInventory: InventoryItem[] = [
  {
    id: '1',
    type: 'modem',
    model: 'ARRIS SB8200',
    serial: 'SB8200001234',
    status: 'available',
    location: 'Truck Inventory',
    lastUpdated: new Date().toISOString(),
    syncStatus: 'synced'
  },
  {
    id: '2',
    type: 'router',
    model: 'ASUS AX6000',
    serial: 'AX6000567890',
    status: 'assigned',
    location: 'Customer Site',
    assignedTo: 'John Doe',
    installationDate: '2023-12-01',
    lastUpdated: new Date().toISOString(),
    syncStatus: 'pending'
  }
];

export const InventoryManagement: React.FC = () => {
  const [inventory, setInventory] = useState<InventoryItem[]>(mockInventory);
  const [filteredInventory, setFilteredInventory] = useState<InventoryItem[]>(mockInventory);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showScanModal, setShowScanModal] = useState(false);
  
  const { 
    isOnline, 
    pendingSync, 
    syncData, 
    addToQueue, 
    retrySync 
  } = useOfflineSync('inventory');

  useEffect(() => {
    // Load inventory from local storage or API
    const loadInventory = async () => {
      try {
        // In offline mode, load from local storage
        if (!isOnline) {
          const localInventory = localStorage.getItem('technicianInventory');
          if (localInventory) {
            setInventory(JSON.parse(localInventory));
          }
        } else {
          // Online - fetch from API
          // const data = await inventoryAPI.getAll();
          // setInventory(data);
        }
      } catch (error) {
        console.error('Failed to load inventory:', error);
      }
    };

    loadInventory();
  }, [isOnline]);

  // Save to local storage whenever inventory changes
  useEffect(() => {
    localStorage.setItem('technicianInventory', JSON.stringify(inventory));
    setFilteredInventory(inventory);
  }, [inventory]);

  const columns = [
    {
      key: 'type' as keyof InventoryItem,
      label: 'Type',
      render: (value: string) => (
        <span className="capitalize bg-gray-100 px-2 py-1 rounded-full text-sm">
          {value}
        </span>
      )
    },
    { key: 'model' as keyof InventoryItem, label: 'Model' },
    { key: 'serial' as keyof InventoryItem, label: 'Serial Number' },
    {
      key: 'status' as keyof InventoryItem,
      label: 'Status',
      render: (value: string) => {
        const colors = {
          available: 'bg-green-100 text-green-800',
          assigned: 'bg-blue-100 text-blue-800',
          installed: 'bg-purple-100 text-purple-800',
          defective: 'bg-red-100 text-red-800',
          returned: 'bg-yellow-100 text-yellow-800'
        };
        return (
          <span className={`px-2 py-1 rounded-full text-sm capitalize ${colors[value as keyof typeof colors]}`}>
            {value}
          </span>
        );
      }
    },
    { key: 'location' as keyof InventoryItem, label: 'Location' },
    {
      key: 'syncStatus' as keyof InventoryItem,
      label: 'Sync',
      render: (value: string, item: InventoryItem) => (
        <div className="flex items-center space-x-1">
          {value === 'synced' && <SignalIcon className="w-4 h-4 text-green-600" />}
          {value === 'pending' && <SignalSlashIcon className="w-4 h-4 text-yellow-600" />}
          {value === 'failed' && (
            <button
              onClick={() => retrySync(item.id)}
              className="text-red-600 hover:text-red-800 text-xs"
            >
              Retry
            </button>
          )}
        </div>
      )
    }
  ];

  const handleSearch = (query: string) => {
    const filtered = inventory.filter(item => 
      item.model.toLowerCase().includes(query.toLowerCase()) ||
      item.serial.toLowerCase().includes(query.toLowerCase()) ||
      item.type.toLowerCase().includes(query.toLowerCase())
    );
    setFilteredInventory(filtered);
  };

  const handleFilter = (filters: Record<string, string>) => {
    let filtered = inventory;
    
    if (filters.type) {
      filtered = filtered.filter(item => item.type === filters.type);
    }
    if (filters.status) {
      filtered = filtered.filter(item => item.status === filters.status);
    }
    if (filters.syncStatus) {
      filtered = filtered.filter(item => item.syncStatus === filters.syncStatus);
    }
    
    setFilteredInventory(filtered);
  };

  const handleAddItem = async (newItem: Omit<InventoryItem, 'id' | 'lastUpdated' | 'syncStatus'>) => {
    const item: InventoryItem = {
      ...newItem,
      id: `temp-${Date.now()}`,
      lastUpdated: new Date().toISOString(),
      syncStatus: isOnline ? 'synced' : 'pending'
    };

    setInventory(prev => [...prev, item]);
    
    // Add to offline sync queue if needed
    if (!isOnline) {
      addToQueue({
        action: 'create',
        resourceType: 'inventory',
        data: item
      });
    } else {
      // Sync immediately when online
      try {
        // await inventoryAPI.create(item);
        // Item synced successfully
      } catch (error) {
        // Mark as failed and add to queue
        item.syncStatus = 'failed';
        addToQueue({
          action: 'create',
          resourceType: 'inventory',
          data: item
        });
      }
    }
  };

  const handleBulkSync = async () => {
    try {
      await syncData();
      // Refresh inventory after sync
      const updated = inventory.map(item => ({ ...item, syncStatus: 'synced' as const }));
      setInventory(updated);
    } catch (error) {
      console.error('Bulk sync failed:', error);
    }
  };

  const actions = [
    {
      label: 'Add Item',
      onClick: () => setShowAddModal(true),
      variant: 'primary' as const,
      icon: PlusIcon
    },
    {
      label: 'Scan QR Code',
      onClick: () => setShowScanModal(true),
      variant: 'secondary' as const,
      icon: QrCodeIcon
    },
    ...(pendingSync > 0 ? [{
      label: `Sync ${pendingSync} Items`,
      onClick: handleBulkSync,
      variant: 'secondary' as const,
      disabled: !isOnline
    }] : [])
  ];

  const filters = [
    {
      key: 'type',
      label: 'Type',
      options: [
        { value: 'modem', label: 'Modem' },
        { value: 'router', label: 'Router' },
        { value: 'cable', label: 'Cable' },
        { value: 'splitter', label: 'Splitter' },
        { value: 'other', label: 'Other' }
      ]
    },
    {
      key: 'status',
      label: 'Status',
      options: [
        { value: 'available', label: 'Available' },
        { value: 'assigned', label: 'Assigned' },
        { value: 'installed', label: 'Installed' },
        { value: 'defective', label: 'Defective' },
        { value: 'returned', label: 'Returned' }
      ]
    },
    {
      key: 'syncStatus',
      label: 'Sync Status',
      options: [
        { value: 'synced', label: 'Synced' },
        { value: 'pending', label: 'Pending' },
        { value: 'failed', label: 'Failed' }
      ]
    }
  ];

  return (
    <>
      <ManagementPageTemplate
        title="Inventory Management"
        subtitle={`${inventory.length} items • ${isOnline ? 'Online' : 'Offline'} ${pendingSync > 0 ? `• ${pendingSync} pending sync` : ''}`}
        data={filteredInventory}
        columns={columns}
        onSearch={handleSearch}
        onFilter={handleFilter}
        actions={actions}
        filters={filters}
        searchPlaceholder="Search by model, serial, or type..."
        emptyMessage="No inventory items found"
        className="h-full"
      />

      {/* Add Item Modal */}
      {showAddModal && (
        <AddInventoryModal
          onClose={() => setShowAddModal(false)}
          onAdd={handleAddItem}
        />
      )}

      {/* QR Code Scanner Modal */}
      {showScanModal && (
        <QRScannerModal
          onClose={() => setShowScanModal(false)}
          onScan={(data) => {
            // Parse QR code data and add item
            // const itemData = parseQRCode(data);
            // handleAddItem(itemData);
            setShowScanModal(false);
          }}
        />
      )}
    </>
  );
};

// Add Item Modal Component
const AddInventoryModal: React.FC<{
  onClose: () => void;
  onAdd: (item: any) => void;
}> = ({ onClose, onAdd }) => {
  const [formData, setFormData] = useState({
    type: 'modem',
    model: '',
    serial: '',
    status: 'available',
    location: 'Truck Inventory',
    notes: ''
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onAdd(formData);
    onClose();
  };

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      role="dialog"
      aria-labelledby="add-item-title"
      aria-modal="true"
    >
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h2 id="add-item-title" className="text-lg font-semibold mb-4">Add Inventory Item</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="item-type" className="block text-sm font-medium text-gray-700 mb-1">
              Type *
            </label>
            <select
              id="item-type"
              value={formData.type}
              onChange={(e) => setFormData({...formData, type: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
              <option value="modem">Modem</option>
              <option value="router">Router</option>
              <option value="cable">Cable</option>
              <option value="splitter">Splitter</option>
              <option value="other">Other</option>
            </select>
          </div>

          <div>
            <label htmlFor="item-model" className="block text-sm font-medium text-gray-700 mb-1">
              Model *
            </label>
            <input
              id="item-model"
              type="text"
              value={formData.model}
              onChange={(e) => setFormData({...formData, model: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div>
            <label htmlFor="item-serial" className="block text-sm font-medium text-gray-700 mb-1">
              Serial Number *
            </label>
            <input
              id="item-serial"
              type="text"
              value={formData.serial}
              onChange={(e) => setFormData({...formData, serial: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div>
            <label htmlFor="item-status" className="block text-sm font-medium text-gray-700 mb-1">
              Status
            </label>
            <select
              id="item-status"
              value={formData.status}
              onChange={(e) => setFormData({...formData, status: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="available">Available</option>
              <option value="assigned">Assigned</option>
              <option value="defective">Defective</option>
            </select>
          </div>

          <div className="flex space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              Add Item
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// QR Scanner Modal Component
const QRScannerModal: React.FC<{
  onClose: () => void;
  onScan: (data: string) => void;
}> = ({ onClose, onScan }) => {
  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      role="dialog"
      aria-labelledby="qr-scanner-title"
      aria-modal="true"
    >
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h2 id="qr-scanner-title" className="text-lg font-semibold mb-4">QR Code Scanner</h2>
        
        <div className="aspect-square bg-gray-100 rounded-lg flex items-center justify-center mb-4">
          <div className="text-center">
            <QrCodeIcon className="w-16 h-16 text-gray-400 mx-auto mb-2" />
            <p className="text-gray-600">Camera view placeholder</p>
            <p className="text-sm text-gray-500 mt-2">
              Scan equipment QR code to auto-populate details
            </p>
          </div>
        </div>

        <div className="flex space-x-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500"
          >
            Cancel
          </button>
          <button
            onClick={() => onScan('mock-qr-data')}
            className="flex-1 px-4 py-2 text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            Test Scan
          </button>
        </div>
      </div>
    </div>
  );
};