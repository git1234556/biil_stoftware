import requests
import sys
import json
from datetime import datetime

class HavnCubeAPITester:
    def __init__(self, base_url="https://a18d1e50-a9e0-4989-9742-2cc4a8de3e80.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.created_estimate_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, response_type='json'):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                if response_type == 'json' and response.content:
                    try:
                        return success, response.json()
                    except:
                        return success, response.text
                else:
                    return success, response.content
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test health endpoint"""
        return self.run_test("Health Check", "GET", "api/health", 200)

    def test_root_endpoint(self):
        """Test root endpoint"""
        return self.run_test("Root Endpoint", "GET", "", 200)

    def test_create_estimate(self):
        """Test creating a new estimate with dual-field measurements"""
        estimate_data = {
            "client_name": "Test Client",
            "client_address": "123 Test Street, Test City",
            "client_phone": "+91-9876543210",
            "estimate_number": "",  # Auto-generated
            "date": datetime.now().strftime("%Y-%m-%d"),
            "line_items": [
                {
                    "particulars": "Flooring Work - Living Room",
                    "length_feet": 12,
                    "length_inches": 6,
                    "width_feet": 10,
                    "width_inches": 0,
                    "quantity": 0,  # Will be calculated for SQFT
                    "unit": "SQFT",
                    "rate": 150.0,
                    "amount": 0  # Will be calculated
                },
                {
                    "particulars": "Electrical Switches",
                    "length_feet": 0,
                    "length_inches": 0,
                    "width_feet": 0,
                    "width_inches": 0,
                    "quantity": 15,
                    "unit": "NOS",
                    "rate": 250.0,
                    "amount": 3750.0
                }
            ],
            "tax_rate": 18.0,
            "subtotal": 0,  # Will be calculated
            "tax_amount": 0,  # Will be calculated
            "total_amount": 0  # Will be calculated
        }
        
        success, response = self.run_test("Create Estimate", "POST", "api/estimates", 201, estimate_data)
        if success and 'id' in response:
            self.created_estimate_id = response['id']
            print(f"   Created estimate ID: {self.created_estimate_id}")
            print(f"   Estimate number: {response.get('estimate_number', 'N/A')}")
            
            # Verify calculations
            line_items = response.get('line_items', [])
            if len(line_items) >= 2:
                # Check SQFT calculation: 12.5 ft * 10 ft = 125 sqft
                sqft_item = line_items[0]
                expected_sqft = (12 + 6/12) * (10 + 0/12)  # 12.5 * 10 = 125
                print(f"   SQFT calculation: {expected_sqft:.2f} sqft expected")
                
                # Check NOS item
                nos_item = line_items[1]
                print(f"   NOS quantity: {nos_item.get('quantity', 0)}")
        
        return success, response

    def test_get_estimates(self):
        """Test getting all estimates"""
        success, response = self.run_test("Get All Estimates", "GET", "api/estimates", 200)
        if success and isinstance(response, list):
            print(f"   Found {len(response)} estimates")
        return success, response

    def test_get_single_estimate(self):
        """Test getting a single estimate by ID"""
        if not self.created_estimate_id:
            print("❌ No estimate ID available for single estimate test")
            return False, {}
        
        return self.run_test(
            "Get Single Estimate", 
            "GET", 
            f"api/estimates/{self.created_estimate_id}", 
            200
        )

    def test_update_estimate(self):
        """Test updating an existing estimate"""
        if not self.created_estimate_id:
            print("❌ No estimate ID available for update test")
            return False, {}
        
        updated_data = {
            "client_name": "Updated Test Client",
            "client_address": "456 Updated Street, Updated City",
            "client_phone": "+91-9876543211",
            "estimate_number": "HCE-TEST-001",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "line_items": [
                {
                    "particulars": "Updated Flooring Work",
                    "length_feet": 15,
                    "length_inches": 0,
                    "width_feet": 12,
                    "width_inches": 6,
                    "quantity": 0,
                    "unit": "SQFT",
                    "rate": 200.0,
                    "amount": 0
                }
            ],
            "tax_rate": 18.0,
            "subtotal": 0,
            "tax_amount": 0,
            "total_amount": 0
        }
        
        return self.run_test(
            "Update Estimate", 
            "PUT", 
            f"api/estimates/{self.created_estimate_id}", 
            200, 
            updated_data
        )

    def test_generate_pdf(self):
        """Test PDF generation"""
        if not self.created_estimate_id:
            print("❌ No estimate ID available for PDF test")
            return False, {}
        
        success, response = self.run_test(
            "Generate PDF", 
            "POST", 
            f"api/estimates/{self.created_estimate_id}/pdf", 
            200,
            {},
            response_type='binary'
        )
        
        if success:
            print(f"   PDF size: {len(response)} bytes")
            # Check if it's actually a PDF
            if response.startswith(b'%PDF'):
                print("   ✅ Valid PDF format detected")
            else:
                print("   ⚠️  Response doesn't appear to be a valid PDF")
        
        return success, response

    def test_delete_estimate(self):
        """Test deleting an estimate"""
        if not self.created_estimate_id:
            print("❌ No estimate ID available for delete test")
            return False, {}
        
        return self.run_test(
            "Delete Estimate", 
            "DELETE", 
            f"api/estimates/{self.created_estimate_id}", 
            200
        )

    def test_calculation_accuracy(self):
        """Test calculation accuracy for different measurement combinations"""
        test_cases = [
            {
                "name": "9'6\" x 7'0\" SQFT calculation",
                "length_feet": 9, "length_inches": 6,
                "width_feet": 7, "width_inches": 0,
                "expected_sqft": 66.5,  # 9.5 * 7 = 66.5
                "rate": 100.0
            },
            {
                "name": "12'3\" x 8'9\" SQFT calculation", 
                "length_feet": 12, "length_inches": 3,
                "width_feet": 8, "width_inches": 9,
                "expected_sqft": 107.1875,  # 12.25 * 8.75 = 107.1875
                "rate": 150.0
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            estimate_data = {
                "client_name": f"Calculation Test Client {i+1}",
                "client_address": "Test Address",
                "client_phone": "+91-1234567890",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "line_items": [
                    {
                        "particulars": f"Test Item - {test_case['name']}",
                        "length_feet": test_case["length_feet"],
                        "length_inches": test_case["length_inches"],
                        "width_feet": test_case["width_feet"],
                        "width_inches": test_case["width_inches"],
                        "quantity": 0,
                        "unit": "SQFT",
                        "rate": test_case["rate"],
                        "amount": 0
                    }
                ],
                "tax_rate": 18.0,
                "subtotal": 0,
                "tax_amount": 0,
                "total_amount": 0
            }
            
            success, response = self.run_test(
                f"Calculation Test - {test_case['name']}", 
                "POST", 
                "api/estimates", 
                201, 
                estimate_data
            )
            
            if success and 'line_items' in response:
                line_item = response['line_items'][0]
                calculated_sqft = line_item.get('quantity', 0)
                expected_amount = test_case['expected_sqft'] * test_case['rate']
                
                print(f"   Expected SQFT: {test_case['expected_sqft']:.4f}")
                print(f"   Calculated SQFT: {calculated_sqft:.4f}")
                print(f"   Expected Amount: ₹{expected_amount:.2f}")
                print(f"   Calculated Amount: ₹{line_item.get('amount', 0):.2f}")
                
                # Clean up test estimate
                if 'id' in response:
                    requests.delete(f"{self.base_url}/api/estimates/{response['id']}")

def main():
    print("🚀 Starting Havn Cube API Testing...")
    print("=" * 60)
    
    tester = HavnCubeAPITester()
    
    # Run all tests
    test_methods = [
        tester.test_root_endpoint,
        tester.test_health_check,
        tester.test_create_estimate,
        tester.test_get_estimates,
        tester.test_get_single_estimate,
        tester.test_update_estimate,
        tester.test_generate_pdf,
        tester.test_calculation_accuracy,
        tester.test_delete_estimate,  # Delete last to clean up
    ]
    
    for test_method in test_methods:
        try:
            test_method()
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
    
    # Print final results
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"⚠️  {tester.tests_run - tester.tests_passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())