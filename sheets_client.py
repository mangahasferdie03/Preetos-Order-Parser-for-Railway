import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, List, Optional, Any
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

class GoogleSheetsClient:
    def __init__(self):
        self.spreadsheet_id = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
        self.service = None
        self._initialize_service()
        
        # Column mappings as per your specification
        self.column_mapping = {
            'order_date': 'C',
            'customer_name': 'D',
            'sold_by': 'E',
            'payment_method': 'G',
            'payment_status': 'H',
            'notes': 'J',
            'order_type': 'K',
            'P-CHZ': 'N',    # Pouch - Cheese
            'P-SC': 'O',     # Pouch - Sour Cream
            'P-BBQ': 'P',    # Pouch - BBQ
            'P-OG': 'Q',     # Pouch - Original
            '2L-CHZ': 'T',   # Tub - Cheese
            '2L-SC': 'U',    # Tub - Sour Cream
            '2L-BBQ': 'V',   # Tub - BBQ
            '2L-OG': 'W',    # Tub - Original
            'shipping_fee': 'Z',
            'discount_amount': 'AA'
        }
        
        # Columns to check for empty rows (D + all product columns)
        self.empty_check_columns = ['D', 'N', 'O', 'P', 'Q', 'T', 'U', 'V', 'W']
        
        # Location to seller mapping
        self.location_to_seller = {
            'Quezon City': 'Ferdie',
            'Paranaque': 'Nina'
        }

    def _initialize_service(self):
        """Initialize Google Sheets API service"""
        try:
            # Get service account credentials from environment variable
            service_account_info = json.loads(os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'))
            
            credentials = Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            
            self.service = build('sheets', 'v4', credentials=credentials)
        except Exception as e:
            print(f"Failed to initialize Google Sheets service: {e}")
            raise

    def find_first_empty_row(self, worksheet_name: str = 'ORDER') -> int:
        """Find the first truly empty row according to the updated rules"""
        try:
            # Fetch range from Row 5 to Row 2422, covering Customer (D) and Product columns (N-W)
            range_name = f"{worksheet_name}!D5:W2422"
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            # Check each row starting from row 5 (index 0 in our fetched data)
            for row_index, row_data in enumerate(values):
                actual_row_number = row_index + 5  # Adjust for starting at row 5
                
                # Pad row_data to ensure we have all columns
                while len(row_data) < 20:  # D to W = 20 columns
                    row_data.append('')
                
                # Check if customer name (column D, index 0 in our range) is empty
                customer_name_empty = not row_data[0].strip() if row_data[0] else True
                
                # Check if all product columns are empty or "0"
                # In range D5:W2422, product columns are:
                # N=index 10, O=index 11, P=index 12, Q=index 13, T=index 16, U=index 17, V=index 18, W=index 19
                product_column_indices = [10, 11, 12, 13, 16, 17, 18, 19]  # N,O,P,Q,T,U,V,W
                product_columns_empty = True
                
                for col_index in product_column_indices:
                    if col_index < len(row_data):
                        cell_value = row_data[col_index].strip() if row_data[col_index] else ""
                        if cell_value and cell_value != "0":
                            product_columns_empty = False
                            break
                
                # If both conditions are met, this is our target row
                if customer_name_empty and product_columns_empty:
                    return actual_row_number
            
            # If no empty row found, return the row after the last row we checked
            return 5 + len(values)
            
        except Exception as e:
            print(f"Error finding empty row: {e}")
            return 643  # Default fallback based on your expected result

    def insert_order(self, parsed_order: Dict[str, Any], worksheet_name: str = 'ORDER') -> bool:
        """Insert parsed order into Google Sheets"""
        try:
            # Find the first empty row
            target_row = self.find_first_empty_row(worksheet_name)
            
            # Prepare the updates dictionary
            updates = {}
            
            # Set app-controlled fields with Philippine timezone
            ph_timezone = ZoneInfo('Asia/Manila')
            current_time = datetime.now(ph_timezone)
            formatted_date = current_time.strftime('%m/%d/%Y')
            print(f"DEBUG: Raw datetime: {current_time}")
            print(f"DEBUG: Formatted date for column C: {formatted_date}")
            updates[self.column_mapping['order_date']] = formatted_date
            
            # Set payment status based on parsed result, default to Unpaid
            payment_status = parsed_order.get('payment_status', 'Unpaid')
            updates[self.column_mapping['payment_status']] = payment_status
            
            updates[self.column_mapping['order_type']] = 'Reserved'
            
            # Use parsed notes if available, otherwise leave empty
            if parsed_order.get('notes'):
                updates[self.column_mapping['notes']] = parsed_order['notes']
            
            # Set customer name
            if parsed_order.get('customer_name'):
                updates[self.column_mapping['customer_name']] = parsed_order['customer_name']
            
            # Set sold by based on location
            if parsed_order.get('customer_location'):
                seller = self.location_to_seller.get(parsed_order['customer_location'])
                if seller:
                    updates[self.column_mapping['sold_by']] = seller
            
            # Set payment method
            if parsed_order.get('payment_method'):
                updates[self.column_mapping['payment_method']] = parsed_order['payment_method']
            
            # Set product quantities
            for item in parsed_order.get('items', []):
                product_code = item['product_code']
                quantity = item['quantity']
                if product_code in self.column_mapping:
                    updates[self.column_mapping[product_code]] = quantity
            
            # Set shipping fee
            if parsed_order.get('shipping_fee'):
                updates[self.column_mapping['shipping_fee']] = parsed_order['shipping_fee']
            
            # Set discount amount
            if parsed_order.get('discount_amount'):
                updates[self.column_mapping['discount_amount']] = parsed_order['discount_amount']
            
            # Prepare batch update
            print(f"DEBUG: Updates dictionary: {updates}")
            requests = []
            for column, value in updates.items():
                print(f"DEBUG: Setting {worksheet_name}!{column}{target_row} = {value} (type: {type(value)})")
                requests.append({
                    'range': f"{worksheet_name}!{column}{target_row}",
                    'values': [[value]]
                })
            
            # Execute batch update
            body = {
                'valueInputOption': 'RAW',
                'data': requests
            }
            
            result = self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=body
            ).execute()
            
            print(f"Successfully inserted order into row {target_row}")
            return True
            
        except Exception as e:
            print(f"Error inserting order: {e}")
            return False

    def get_order_summary(self, parsed_order: Dict[str, Any]) -> str:
        """Generate a summary of the order for confirmation"""
        summary_lines = []
        
        if parsed_order.get('customer_name'):
            summary_lines.append(f"Customer: {parsed_order['customer_name']}")
        
        # Items
        if parsed_order.get('items'):
            summary_lines.append("Items:")
            for item in parsed_order['items']:
                product_code = item['product_code']
                quantity = item['quantity']
                # Get product info for readable name
                size = "Tub" if product_code.startswith('2L') else "Pouch"
                flavor_code = product_code.split('-')[1]
                flavor_map = {'CHZ': 'Cheese', 'SC': 'Sour Cream', 'BBQ': 'BBQ', 'OG': 'Original'}
                flavor = flavor_map.get(flavor_code, flavor_code)
                summary_lines.append(f"  • {quantity}x {size} {flavor}")
        
        # Payment and location
        if parsed_order.get('payment_method'):
            summary_lines.append(f"Payment: {parsed_order['payment_method']}")
        
        if parsed_order.get('customer_location'):
            summary_lines.append(f"Location: {parsed_order['customer_location']}")
        
        # Fees and discounts
        if parsed_order.get('shipping_fee'):
            summary_lines.append(f"Shipping: ₱{parsed_order['shipping_fee']}")
        
        if parsed_order.get('discount_percentage'):
            summary_lines.append(f"Discount: {parsed_order['discount_percentage']}%")
            if parsed_order.get('discount_amount'):
                summary_lines.append(f"Discount Amount: ₱{parsed_order['discount_amount']}")
        
        return '\n'.join(summary_lines)