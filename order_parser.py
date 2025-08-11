import json
import re
import os
from typing import Dict, List, Optional, Tuple, Any
from anthropic import Anthropic

class OrderParser:
    def __init__(self):
        self.anthropic_client = None
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if anthropic_key:
            try:
                self.anthropic_client = Anthropic(api_key=anthropic_key)
            except Exception as e:
                print(f"Failed to initialize Anthropic client: {e}")
                self.anthropic_client = None
        
        # Product catalog
        self.products = {
            'P-CHZ': {'name': 'Cheese', 'size': 'Pouch', 'price': 150},
            'P-SC': {'name': 'Sour Cream', 'size': 'Pouch', 'price': 150},
            'P-BBQ': {'name': 'BBQ', 'size': 'Pouch', 'price': 150},
            'P-OG': {'name': 'Original', 'size': 'Pouch', 'price': 150},
            '2L-CHZ': {'name': 'Cheese', 'size': 'Tub', 'price': 290},
            '2L-SC': {'name': 'Sour Cream', 'size': 'Tub', 'price': 290},
            '2L-BBQ': {'name': 'BBQ', 'size': 'Tub', 'price': 290},
            '2L-OG': {'name': 'Original', 'size': 'Tub', 'price': 290}
        }
        
        # Aliases for flavors
        self.flavor_aliases = {
            'cheese': 'CHZ', 'cheesy': 'CHZ', 'keso': 'CHZ',
            'sour cream': 'SC', 'sour': 'SC', 'sc': 'SC',
            'bbq': 'BBQ', 'barbeque': 'BBQ', 'barbecue': 'BBQ',
            'original': 'OG', 'plain': 'OG', 'orig': 'OG'
        }
        
        # Size indicators
        self.size_indicators = {
            'pouch': 'P', 'maliit': 'P', '100g': 'P', '100 grams': 'P',
            'tub': '2L', 'malaki': '2L', '200g': '2L', '200 grams': '2L'
        }
        
        # Filipino numbers
        self.filipino_numbers = {
            'isa': 1, 'isang': 1, 'dalawa': 2, 'tatlo': 3, 'apat': 4,
            'lima': 5, 'anim': 6, 'pito': 7, 'walo': 8, 'siyam': 9,
            'sampu': 10, 'sampung': 10
        }

    def parse_order(self, message: str) -> Dict[str, Any]:
        """Main parsing function with Claude AI primary and regex fallback"""
        try:
            if self.anthropic_client:
                return self._parse_with_claude(message)
        except Exception as e:
            print(f"Claude parsing failed: {e}")
        
        # Fallback to regex parsing
        return self._parse_with_regex(message)

    def _parse_with_claude(self, message: str) -> Dict[str, Any]:
        """Parse using Claude AI with detailed prompt"""
        
        prompt = f"""Parse this order message into valid JSON only (no extra text). Follow these exact rules:

PRODUCT CATALOG:
- P-CHZ (Pouch Cheese) - 150 pesos
- P-SC (Pouch Sour Cream) - 150 pesos  
- P-BBQ (Pouch BBQ) - 150 pesos
- P-OG (Pouch Original) - 150 pesos
- 2L-CHZ (Tub Cheese) - 290 pesos
- 2L-SC (Tub Sour Cream) - 290 pesos
- 2L-BBQ (Tub BBQ) - 290 pesos
- 2L-OG (Tub Original) - 290 pesos

ALIASES:
- Flavors: cheese/cheesy/keso→CHZ, sour cream/sour/sc→SC, bbq/barbeque/barbecue→BBQ, original/plain/orig→OG
- Sizes: pouch/maliit/100g→P-, tub/malaki/200g→2L-
- Numbers: isa/isang→1, dalawa→2, tatlo→3, apat→4, lima→5, etc.

PARSING RULES:
- customer_name: extract name, title case
- payment_method: "Gcash"|"BPI"|"Maya"|"Cash"|"BDO"|"Others"|null
- customer_location: "Quezon City" (from QC/quezon city) | "Paranaque" | null  
- discount_percentage: number (interpret all discounts as %), null if none
- discount_amount: calculate from subtotal if percentage given, null otherwise
- shipping_fee: extract peso amount from "sf/shipping/delivery/padala/hatid [number]"
- items: array of {{"product_code": string, "quantity": number}}
- confidence: 0-1 score
- notes: brief parsing explanation

MODIFICATIONS (chronological order):
- Process add/remove/replace commands step by step
- "add pa/pa-add/dagdag/plus/at saka/pati/kasama" = add
- "patanggal/tanggal/remove/wag na/cancel/hindi na" = remove  
- "replace/pareplace/palit/change to/instead of" = remove old, add new
- Removed items must NOT appear in final items array

MESSAGE TO PARSE:
{message}

Return only valid JSON matching this schema:
{{
  "customer_name": string|null,
  "payment_method": string|null,
  "customer_location": string|null,
  "discount_percentage": number|null,
  "discount_amount": number|null,
  "shipping_fee": number|null,
  "items": [{{"product_code": string, "quantity": number}}],
  "confidence": number,
  "notes": string
}}"""

        response = self.anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        json_text = response.content[0].text.strip()
        result = json.loads(json_text)
        
        # Validate and compute discount amount if needed
        return self._validate_and_process(result)

    def _parse_with_regex(self, message: str) -> Dict[str, Any]:
        """Regex-based fallback parser"""
        result = {
            "customer_name": None,
            "payment_method": None,
            "customer_location": None,
            "discount_percentage": None,
            "discount_amount": None,
            "shipping_fee": None,
            "items": [],
            "confidence": 0.7,
            "notes": "Parsed using regex fallback"
        }
        
        lines = [line.strip() for line in message.split('\n') if line.strip()]
        
        for line in lines:
            line_lower = line.lower()
            
            # Extract customer name (first line if it's just a name)
            if not result["customer_name"] and len(line.split()) <= 3 and not any(keyword in line_lower for keyword in ['pouch', 'tub', 'gcash', 'bpi', 'maya']):
                result["customer_name"] = line.title()
                continue
            
            # Extract payment method
            if any(method in line_lower for method in ['gcash', 'g-cash', 'g cash']):
                result["payment_method"] = "Gcash"
            elif 'bpi' in line_lower:
                result["payment_method"] = "BPI"
            elif any(method in line_lower for method in ['maya', 'paymaya', 'pay maya']):
                result["payment_method"] = "Maya"
            elif any(method in line_lower for method in ['cash', 'cod', 'cash on delivery']):
                result["payment_method"] = "Cash"
            elif 'bdo' in line_lower:
                result["payment_method"] = "BDO"
            
            # Extract location
            if any(loc in line_lower for loc in ['qc', 'quezon city', 'quezon']):
                result["customer_location"] = "Quezon City"
            elif any(loc in line_lower for loc in ['paranaque', 'parañaque', 'paranañaque']):
                result["customer_location"] = "Paranaque"
            
            # Extract shipping fee
            sf_match = re.search(r'(?:sf|shipping|delivery|padala|hatid).*?(\d+)', line_lower)
            if sf_match:
                result["shipping_fee"] = int(sf_match.group(1))
            
            # Extract discount
            discount_match = re.search(r'(?:discount|off|bawas).*?(\d+)', line_lower)
            if discount_match:
                result["discount_percentage"] = float(discount_match.group(1))
            
            # Extract items
            items = self._extract_items_regex(line)
            result["items"].extend(items)
        
        # Calculate discount amount
        if result["discount_percentage"] and result["items"]:
            subtotal = sum(self.products[item["product_code"]]["price"] * item["quantity"] 
                          for item in result["items"])
            result["discount_amount"] = int(subtotal * (result["discount_percentage"] / 100))
        
        return result

    def _extract_items_regex(self, line: str) -> List[Dict[str, Any]]:
        """Extract items from a line using regex"""
        items = []
        line_lower = line.lower()
        
        # Pattern: [quantity] [size] [flavor]
        pattern = r'(\d+|' + '|'.join(self.filipino_numbers.keys()) + r')\s*(?:x\s*)?(?:(pouch|tub|maliit|malaki|100g|200g)\s+)?([a-z\s]+)'
        
        matches = re.findall(pattern, line_lower)
        
        for match in matches:
            quantity_str, size_hint, flavor_text = match
            
            # Convert quantity
            if quantity_str.isdigit():
                quantity = int(quantity_str)
            else:
                quantity = self.filipino_numbers.get(quantity_str, 1)
            
            # Determine flavor
            flavor_code = None
            for alias, code in self.flavor_aliases.items():
                if alias in flavor_text:
                    flavor_code = code
                    break
            
            if not flavor_code:
                continue
            
            # Determine size
            size_prefix = 'P'  # Default to pouch
            if size_hint:
                for indicator, prefix in self.size_indicators.items():
                    if indicator in size_hint:
                        size_prefix = prefix
                        break
            
            product_code = f"{size_prefix}-{flavor_code}"
            if product_code in self.products:
                items.append({"product_code": product_code, "quantity": quantity})
        
        return items

    def _validate_and_process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parsed result and compute missing fields"""
        
        # Title case customer name
        if result.get("customer_name"):
            result["customer_name"] = result["customer_name"].title()
        
        # Compute discount amount if percentage given but amount missing
        if result.get("discount_percentage") and not result.get("discount_amount") and result.get("items"):
            subtotal = sum(self.products[item["product_code"]]["price"] * item["quantity"] 
                          for item in result["items"] if item["product_code"] in self.products)
            result["discount_amount"] = int(subtotal * (result["discount_percentage"] / 100))
        
        # Validate product codes
        valid_items = []
        for item in result.get("items", []):
            if item["product_code"] in self.products and item["quantity"] >= 1:
                valid_items.append(item)
        result["items"] = valid_items
        
        return result