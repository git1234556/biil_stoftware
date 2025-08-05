import React, { useState, useEffect } from 'react';
import { Plus, Download, Edit3, Trash2, FileText, Calculator } from 'lucide-react';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card';
import { Textarea } from './components/ui/textarea';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './components/ui/dialog';
import { Badge } from './components/ui/badge';
import './App.css';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_BACKEND_URL;

// Measurement Input Component
const MeasurementInput = ({ label, feetValue, inchesValue, onFeetChange, onInchesChange, disabled = false }) => {
  return (
    <div className="flex flex-col space-y-2">
      <Label className="text-sm font-medium text-gray-700">{label}</Label>
      <div className="flex space-x-2">
        <div className="flex items-center space-x-1">
          <Input
            type="number"
            placeholder="0"
            value={feetValue || ''}
            onChange={(e) => onFeetChange(parseInt(e.target.value) || 0)}
            className="w-16 text-center"
            min="0"
            disabled={disabled}
          />
          <span className="text-sm text-gray-500">ft</span>
        </div>
        <div className="flex items-center space-x-1">
          <Input
            type="number"
            placeholder="0"
            value={inchesValue || ''}
            onChange={(e) => onInchesChange(parseInt(e.target.value) || 0)}
            className="w-16 text-center"
            min="0"
            max="11"
            disabled={disabled}
          />
          <span className="text-sm text-gray-500">in</span>
        </div>
      </div>
    </div>
  );
};

// Line Item Component
const LineItemRow = ({ item, index, onUpdate, onDelete }) => {
  const calculateQuantity = (item) => {
    if (item.unit === 'SQFT') {
      const length = (item.length_feet || 0) + (item.length_inches || 0) / 12;
      const width = (item.width_feet || 0) + (item.width_inches || 0) / 12;
      return length * width;
    }
    return item.quantity || 0;
  };

  const calculateAmount = (item) => {
    const qty = calculateQuantity(item);
    return qty * (item.rate || 0);
  };

  const handleItemChange = (field, value) => {
    const updatedItem = { ...item, [field]: value };
    
    // Auto-calculate amount when rate or dimensions change
    const qty = calculateQuantity(updatedItem);
    updatedItem.quantity = qty;
    updatedItem.amount = qty * (updatedItem.rate || 0);
    
    onUpdate(index, updatedItem);
  };

  const displayQuantity = calculateQuantity(item);
  const displayAmount = calculateAmount(item);

  return (
    <TableRow className="hover:bg-gray-50 transition-colors">
      <TableCell className="font-medium">{index + 1}</TableCell>
      <TableCell>
        <Textarea
          value={item.particulars || ''}
          onChange={(e) => handleItemChange('particulars', e.target.value)}
          placeholder="Description of work..."
          className="min-h-[60px] resize-none"
        />
      </TableCell>
      <TableCell>
        {item.unit === 'SQFT' ? (
          <div className="space-y-3">
            <MeasurementInput
              label="Length"
              feetValue={item.length_feet}
              inchesValue={item.length_inches}
              onFeetChange={(value) => handleItemChange('length_feet', value)}
              onInchesChange={(value) => handleItemChange('length_inches', value)}
            />
            <MeasurementInput
              label="Width"
              feetValue={item.width_feet}
              inchesValue={item.width_inches}
              onFeetChange={(value) => handleItemChange('width_feet', value)}
              onInchesChange={(value) => handleItemChange('width_inches', value)}
            />
            <div className="text-sm font-medium text-green-700 bg-green-50 p-2 rounded">
              SQFT: {displayQuantity.toFixed(2)}
            </div>
          </div>
        ) : (
          <Input
            type="number"
            value={item.quantity || ''}
            onChange={(e) => handleItemChange('quantity', parseFloat(e.target.value) || 0)}
            placeholder="0"
            min="0"
            step="0.01"
          />
        )}
      </TableCell>
      <TableCell>
        <Select 
          value={item.unit || 'SQFT'} 
          onValueChange={(value) => handleItemChange('unit', value)}
        >
          <SelectTrigger>
            <SelectValue placeholder="Unit" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="SQFT">SQFT</SelectItem>
            <SelectItem value="NOS">NOS</SelectItem>
          </SelectContent>
        </Select>
      </TableCell>
      <TableCell>
        <Input
          type="number"
          value={item.rate || ''}
          onChange={(e) => handleItemChange('rate', parseFloat(e.target.value) || 0)}
          placeholder="0.00"
          min="0"
          step="0.01"
        />
      </TableCell>
      <TableCell className="font-medium">
        ₹{displayAmount.toFixed(2)}
      </TableCell>
      <TableCell>
        <Button
          variant="destructive"
          size="sm"
          onClick={() => onDelete(index)}
          className="hover:bg-red-600"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </TableCell>
    </TableRow>
  );
};

// Main App Component
function App() {
  const [estimates, setEstimates] = useState([]);
  const [currentEstimate, setCurrentEstimate] = useState(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    client_name: '',
    client_address: '',
    client_phone: '',
    estimate_number: '',
    date: new Date().toISOString().split('T')[0],
    line_items: [],
    tax_rate: 18.0
  });

  useEffect(() => {
    fetchEstimates();
  }, []);

  const fetchEstimates = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/estimates`);
      setEstimates(response.data);
    } catch (error) {
      console.error('Error fetching estimates:', error);
    }
  };

  const calculateTotals = (lineItems) => {
    const subtotal = lineItems.reduce((sum, item) => {
      const qty = item.unit === 'SQFT' 
        ? ((item.length_feet || 0) + (item.length_inches || 0) / 12) * 
          ((item.width_feet || 0) + (item.width_inches || 0) / 12)
        : (item.quantity || 0);
      return sum + (qty * (item.rate || 0));
    }, 0);

    const taxAmount = subtotal * (formData.tax_rate / 100);
    const total = subtotal + taxAmount;

    return { subtotal, taxAmount, total };
  };

  const addLineItem = () => {
    const newItem = {
      id: '',
      particulars: '',
      length_feet: 0,
      length_inches: 0,
      width_feet: 0,
      width_inches: 0,
      quantity: 0,
      unit: 'SQFT',
      rate: 0,
      amount: 0
    };
    
    setFormData(prev => ({
      ...prev,
      line_items: [...prev.line_items, newItem]
    }));
  };

  const updateLineItem = (index, updatedItem) => {
    const newLineItems = [...formData.line_items];
    newLineItems[index] = updatedItem;
    
    setFormData(prev => ({
      ...prev,
      line_items: newLineItems
    }));
  };

  const deleteLineItem = (index) => {
    setFormData(prev => ({
      ...prev,
      line_items: prev.line_items.filter((_, i) => i !== index)
    }));
  };

  const saveEstimate = async () => {
    try {
      const { subtotal, taxAmount, total } = calculateTotals(formData.line_items);
      
      const estimateData = {
        ...formData,
        subtotal,
        tax_amount: taxAmount,
        total_amount: total
      };

      if (currentEstimate) {
        await axios.put(`${API_BASE}/api/estimates/${currentEstimate.id}`, estimateData);
      } else {
        await axios.post(`${API_BASE}/api/estimates`, estimateData);
      }

      await fetchEstimates();
      resetForm();
      setIsDialogOpen(false);
    } catch (error) {
      console.error('Error saving estimate:', error);
    }
  };

  const downloadPDF = async (estimateId) => {
    try {
      const response = await axios.post(`${API_BASE}/api/estimates/${estimateId}/pdf`, {}, {
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `Estimate_${estimateId}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading PDF:', error);
    }
  };

  const editEstimate = (estimate) => {
    setCurrentEstimate(estimate);
    setFormData({
      client_name: estimate.client_name,
      client_address: estimate.client_address,
      client_phone: estimate.client_phone,
      estimate_number: estimate.estimate_number,
      date: estimate.date,
      line_items: estimate.line_items,
      tax_rate: estimate.tax_rate
    });
    setIsDialogOpen(true);
  };

  const deleteEstimate = async (estimateId) => {
    if (window.confirm('Are you sure you want to delete this estimate?')) {
      try {
        await axios.delete(`${API_BASE}/api/estimates/${estimateId}`);
        await fetchEstimates();
      } catch (error) {
        console.error('Error deleting estimate:', error);
      }
    }
  };

  const resetForm = () => {
    setCurrentEstimate(null);
    setFormData({
      client_name: '',
      client_address: '',
      client_phone: '',
      estimate_number: '',
      date: new Date().toISOString().split('T')[0],
      line_items: [],
      tax_rate: 18.0
    });
  };

  const { subtotal, taxAmount, total } = calculateTotals(formData.line_items);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="h-12 w-12 bg-gradient-to-br from-blue-600 to-purple-600 rounded-xl flex items-center justify-center">
                <Calculator className="h-7 w-7 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Havn Cube</h1>
                <p className="text-gray-500">Billing & Estimation Tool</p>
              </div>
            </div>
            
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
              <DialogTrigger asChild>
                <Button 
                  onClick={resetForm}
                  className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 shadow-lg"
                >
                  <Plus className="mr-2 h-4 w-4" />
                  New Estimate
                </Button>
              </DialogTrigger>
              
              <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle className="text-xl">
                    {currentEstimate ? 'Edit Estimate' : 'Create New Estimate'}
                  </DialogTitle>
                </DialogHeader>
                
                <div className="space-y-6">
                  {/* Client Information */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Client Information</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <Label htmlFor="client_name">Client Name *</Label>
                          <Input
                            id="client_name"
                            value={formData.client_name}
                            onChange={(e) => setFormData(prev => ({ ...prev, client_name: e.target.value }))}
                            placeholder="Enter client name"
                            className="mt-1"
                          />
                        </div>
                        <div>
                          <Label htmlFor="client_phone">Phone Number</Label>
                          <Input
                            id="client_phone"
                            value={formData.client_phone}
                            onChange={(e) => setFormData(prev => ({ ...prev, client_phone: e.target.value }))}
                            placeholder="Enter phone number"
                            className="mt-1"
                          />
                        </div>
                      </div>
                      <div>
                        <Label htmlFor="client_address">Address</Label>
                        <Textarea
                          id="client_address"
                          value={formData.client_address}
                          onChange={(e) => setFormData(prev => ({ ...prev, client_address: e.target.value }))}
                          placeholder="Enter client address"
                          className="mt-1"
                          rows={2}
                        />
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <Label htmlFor="estimate_number">Estimate Number</Label>
                          <Input
                            id="estimate_number"
                            value={formData.estimate_number}
                            onChange={(e) => setFormData(prev => ({ ...prev, estimate_number: e.target.value }))}
                            placeholder="Auto-generated if empty"
                            className="mt-1"
                          />
                        </div>
                        <div>
                          <Label htmlFor="date">Date</Label>
                          <Input
                            id="date"
                            type="date"
                            value={formData.date}
                            onChange={(e) => setFormData(prev => ({ ...prev, date: e.target.value }))}
                            className="mt-1"
                          />
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Line Items */}
                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between">
                      <CardTitle className="text-lg">Line Items</CardTitle>
                      <Button onClick={addLineItem} size="sm" variant="outline">
                        <Plus className="mr-2 h-4 w-4" />
                        Add Item
                      </Button>
                    </CardHeader>
                    <CardContent>
                      <div className="overflow-x-auto">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead className="w-16">Sn</TableHead>
                              <TableHead className="min-w-[200px]">Particulars</TableHead>
                              <TableHead className="min-w-[200px]">Quantity</TableHead>
                              <TableHead className="w-24">Unit</TableHead>
                              <TableHead className="w-32">Rate (₹)</TableHead>
                              <TableHead className="w-32">Amount (₹)</TableHead>
                              <TableHead className="w-16">Action</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {formData.line_items.map((item, index) => (
                              <LineItemRow
                                key={index}
                                item={item}
                                index={index}
                                onUpdate={updateLineItem}
                                onDelete={deleteLineItem}
                              />
                            ))}
                            {formData.line_items.length === 0 && (
                              <TableRow>
                                <TableCell colSpan={7} className="text-center py-8 text-gray-500">
                                  No line items added yet. Click "Add Item" to get started.
                                </TableCell>
                              </TableRow>
                            )}
                          </TableBody>
                        </Table>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Totals */}
                  {formData.line_items.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-lg">Totals</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2 max-w-sm ml-auto">
                          <div className="flex justify-between">
                            <span>Subtotal:</span>
                            <span className="font-medium">₹{subtotal.toFixed(2)}</span>
                          </div>
                          <div className="flex justify-between items-center">
                            <div className="flex items-center space-x-2">
                              <span>Tax:</span>
                              <Input
                                type="number"
                                value={formData.tax_rate}
                                onChange={(e) => setFormData(prev => ({ ...prev, tax_rate: parseFloat(e.target.value) || 0 }))}
                                className="w-16 h-6 text-sm"
                                min="0"
                                max="100"
                                step="0.1"
                              />
                              <span>%</span>
                            </div>
                            <span className="font-medium">₹{taxAmount.toFixed(2)}</span>
                          </div>
                          <hr />
                          <div className="flex justify-between text-lg font-bold">
                            <span>Total:</span>
                            <span>₹{total.toFixed(2)}</span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {/* Action Buttons */}
                  <div className="flex justify-end space-x-4">
                    <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button 
                      onClick={saveEstimate}
                      disabled={!formData.client_name || formData.line_items.length === 0}
                      className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                    >
                      {currentEstimate ? 'Update Estimate' : 'Save Estimate'}
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-2">Recent Estimates</h2>
          <p className="text-gray-600">Manage your project estimates and generate professional PDFs</p>
        </div>

        {estimates.length === 0 ? (
          <Card className="text-center py-12">
            <CardContent>
              <FileText className="h-16 w-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No estimates yet</h3>
              <p className="text-gray-500 mb-6">Create your first estimate to get started</p>
              <Button 
                onClick={() => setIsDialogOpen(true)}
                className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
              >
                <Plus className="mr-2 h-4 w-4" />
                Create First Estimate
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {estimates.map((estimate) => (
              <Card key={estimate.id} className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">{estimate.estimate_number}</CardTitle>
                    <Badge variant="outline">{estimate.line_items?.length || 0} items</Badge>
                  </div>
                  <div className="text-sm text-gray-600">
                    <p className="font-medium">{estimate.client_name}</p>
                    <p>{estimate.date}</p>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 mb-4">
                    <div className="flex justify-between text-sm">
                      <span>Subtotal:</span>
                      <span>₹{(estimate.subtotal || 0).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Tax:</span>
                      <span>₹{(estimate.tax_amount || 0).toFixed(2)}</span>
                    </div>
                    <hr />
                    <div className="flex justify-between font-bold">
                      <span>Total:</span>
                      <span>₹{(estimate.total_amount || 0).toFixed(2)}</span>
                    </div>
                  </div>
                  
                  <div className="flex space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => editEstimate(estimate)}
                      className="flex-1"
                    >
                      <Edit3 className="mr-2 h-4 w-4" />
                      Edit
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => downloadPDF(estimate.id)}
                      className="flex-1"
                    >
                      <Download className="mr-2 h-4 w-4" />
                      PDF
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => deleteEstimate(estimate.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-16">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="text-center">
            <h3 className="font-bold text-lg text-gray-900">Havn Cube</h3>
            <p className="text-gray-600 mt-1">Interior Design & Execution</p>
            <p className="text-sm text-gray-500 mt-2">
              Contact: +91-XXXXXXXXXX | Email: info@havncube.com
            </p>
            <p className="text-xs text-gray-400 mt-4">
              © 2025 Havn Cube. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;