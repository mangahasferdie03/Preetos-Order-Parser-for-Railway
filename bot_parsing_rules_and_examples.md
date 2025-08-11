# Bot Parsing Rules & Examples (Preetos.ai)

This document defines **exactly how the Telegram bot should parse messages** using the Anthropic LLM and **how the parsed fields map into Google Sheets**. Use this to implement/“vibe code” the parsing behavior so the bot’s output is consistent with the app.

---

## End-to-end flow (Telegram → Sheets)
1. **User sends a message** to the Telegram bot (English/Tagalog/Taglish).
2. **LLM parses the message** into a strict JSON object (spec below). If the LLM is unavailable, a regex fallback runs (not covered here).
3. **App maps the JSON fields to Google Sheet columns** (see Column Mapping), **finds the first truly empty row**, and updates cells for that row only.

> “First truly empty row” rule = Column **D** and **all** product columns (**N, O, P, Q, T, U, V, W**) are blank or “0”.

---

## JSON Output Schema (from LLM)
LLM must return **valid JSON only** (no extra text) with these fields:

```json
{
  "customer_name": "extracted name or null",
  "payment_method": "Gcash" | "BPI" | "Maya" | "Cash" | "BDO" | "Others" | null,
  "customer_location": "Quezon City" | "Paranaque" | null,
  "discount_percentage": number | null,
  "discount_amount": number | null,
  "shipping_fee": number | null,
  "items": [
    {"product_code": "P-CHZ", "quantity": 2},
    {"product_code": "2L-BBQ", "quantity": 1}
  ],
  "confidence": number,
  "notes": "short parsing notes or steps"
}
```

### Notes
- If **discount_percentage** exists but **discount_amount** is not provided, the app will compute it from the items subtotal using `int(subtotal * (discount_percentage / 100))`.
- `customer_name` is title-cased by the app post-parse.
- The app stores shipping fee and discount amount in their own columns (it **does not** apply them to `total_amount` on the sheet).

---

## Product Catalog (allowed product_code values)
| Code     | Canonical Name (pouch/tub label)        | Size  | Price |
|----------|------------------------------------------|-------|-------|
| P-CHZ    | Cheese                                   | Pouch | 150   |
| P-SC     | Sour Cream                               | Pouch | 150   |
| P-BBQ    | BBQ                                      | Pouch | 150   |
| P-OG     | Original / Original Blend                | Pouch | 150   |
| 2L-CHZ   | Cheese                                   | Tub   | 290   |
| 2L-SC    | Sour Cream                               | Tub   | 290   |
| 2L-BBQ   | BBQ                                      | Tub   | 290   |
| 2L-OG    | Original / Original Spice Blend          | Tub   | 290   |

### Alias & Size Recognition (Taglish-friendly)
- **Flavor aliases** → product family:  
  - Cheese: “cheese”, “cheesy”, “keso”  
  - Sour Cream: “sour cream”, “sour”, “sc”  
  - BBQ: “bbq”, “barbeque”, “barbecue”  
  - Original: “original”, “plain”, “orig”
- **Size cues**:  
  - Pouch: “pouch”, “maliit”, “100g”, “100 grams”  
  - Tub: “tub”, “malaki”, “200g”, “200 grams”  
- **Grams imply size**: “100g” → pouch; “200g” → tub.

---

## Quantity Recognition
- Numeric forms: `1`, `2`, `3`, …
- Filipino number words are acceptable: “isang/isa”, “dalawa”, “tatlo”, “apat”, “lima”, “anim”, “pito”, “walo”, “siyam”, “sampu/sampung”.

---

## Modification Semantics (must follow chronological order)
Process the message **as a running order** and apply changes step-by-step:

- **Add**: “add pa”, “pa-add”, “dagdag pa”, “plus”, “at saka”, “pati”, “kasama”.  
- **Remove**: “patanggal”, “tanggal”, “remove”, “wag na”, “cancel”, “hindi na”.  
- **Replace**: “replace/pareplace/palit/change to/instead of”. **Delete old first, then add new**.

**Hard rule:** Any item explicitly removed must **not** appear in the final `items` array.

Include a brief audit trail in **`notes`** summarizing the steps (e.g., “Removed 1 × 2L-CHZ; Added 3 × 2L-SC; Added 1 × 2L-OG”).

---

## Payment, Location, Discount, Shipping

### Payment Method (normalized enum)
- **Gcash**: “gcash”, “g-cash”, “g cash”  
- **BPI**: “bpi”  
- **Maya**: “maya”, “paymaya”, “pay maya”  
- **Cash**: “cash”, “cod”, “cash on delivery”, “bayad cash”  
- **BDO**: “bdo”  
- **Others**: any bank/transfer wording not in the above  
- If none detected → `null`

### Location → Seller Mapping
- LLM returns only `customer_location` (if detected):  
  - “Quezon City”, “QC”, “quezon city”, “qc” → **"Quezon City"**  
  - “Paranaque”, “Parañaque”, “Paranañaque” → **"Paranaque"**
- The **app** maps location to **Sold By (Column E)**:  
  - Quezon City → **Ferdie**  
  - Paranaque → **Nina**

### Discounts (percentage-based only)
- Interpret **all numeric discounts as percentages**:  
  - Examples: “15% off”, “15% discount”, “15%”, “discount 5” ⇒ 5%  
  - Bare “discount/diskarte/bawas” with no number ⇒ `discount_percentage: 0.0`, `discount_amount: 0`  
- App computes `discount_amount` if only `%` is given.

### Shipping Fee (peso amount only)
- Extract integers from phrases like:  
  “shipping 50”, “shipping fee 75”, “delivery 100”, “sf 60”, “padala 50”, “hatid 75”, “50 shipping”, “plus 50 shipping”.  
- Always a fixed peso value (never a %).

---

## Column Mapping (Sheet Updates)
After parsing, the app updates the following columns **for the chosen row**:

| Column | Purpose                                        |
|--------|------------------------------------------------|
| **C**  | Order Date (today, set by app)                |
| **D**  | Customer Name                                  |
| **E**  | Sold By (auto-assigned via location)           |
| **G**  | Payment Method                                 |
| **H**  | Payment Status (always “Unpaid”)               |
| **J**  | Notes (🤖 + timestamp, set by app)             |
| **K**  | Order Type (always “Reserved”, set by app)     |
| **N**  | Pouch – Cheese (`P-CHZ`)                       |
| **O**  | Pouch – Sour Cream (`P-SC`)                    |
| **P**  | Pouch – BBQ (`P-BBQ`)                          |
| **Q**  | Pouch – Original Blend (`P-OG`)                |
| **T**  | Tub – Cheese (`2L-CHZ`)                        |
| **U**  | Tub – Sour Cream (`2L-SC`)                     |
| **V**  | Tub – BBQ (`2L-BBQ`)                           |
| **W**  | Tub – Original Spice Blend (`2L-OG`)           |
| **Z**  | Shipping Fee                                   |
| **AA** | Discount Amount                                |

> Columns **E/J/K/H/C** are app-driven defaults (not decided by the LLM). The LLM sets content that leads to **E** only via `customer_location` → seller mapping.

---

## Acceptance Checks
1. Response is **valid JSON** only (no prose).  
2. `items[*].product_code` ∈ {P-CHZ, P-SC, P-BBQ, P-OG, 2L-CHZ, 2L-SC, 2L-BBQ, 2L-OG}; `quantity` ≥ 1.  
3. Removed items do **not** appear in the final `items`.  
4. `payment_method` and `customer_location` match the enums above (or `null`).  
5. `discount_percentage` is %; `discount_amount` is peso value; `shipping_fee` is peso value.  

---

## Examples

### Example A — Simple with shipping and discount
**Message**
```
ferdie
1 pouch cheese
sf 100
discount 5
```

**LLM JSON**
```json
{
  "customer_name": "Ferdie",
  "payment_method": null,
  "customer_location": null,
  "discount_percentage": 5.0,
  "discount_amount": 7,
  "shipping_fee": 100,
  "items": [
    {"product_code": "P-CHZ", "quantity": 1}
  ],
  "confidence": 0.92,
  "notes": "Parsed '1 pouch cheese' → P-CHZ x1; 'sf 100' → shipping_fee=100; 'discount 5' → 5%."
}
```
**Sheet columns updated**
- **D** = Ferdie
- **N** = 1
- **Z** = 100
- **AA** = 7
- **C** = today (by app), **H** = “Unpaid”, **K** = “Reserved”, **J** = “🤖 HH:MM AM/PM” (by app)
- **E** remains blank (no location)

---

### Example B — Taglish + modifications (from test case)
**Message (single block):**
```
isang tub cheese po tapos padd na rin ng tatlong bbq pouch
ay wait pwede patanggal yung tub cheese tapos pa-add na lang ng 3 sour cream tub
tapos padd ng isa pang original blend na tub
```

**LLM JSON (final items only):**
```json
{
  "customer_name": null,
  "payment_method": null,
  "customer_location": null,
  "discount_percentage": null,
  "discount_amount": null,
  "shipping_fee": null,
  "items": [
    {"product_code": "P-BBQ", "quantity": 3},
    {"product_code": "2L-SC", "quantity": 3},
    {"product_code": "2L-OG", "quantity": 1}
  ],
  "confidence": 0.9,
  "notes": "Removed 1×2L-CHZ; Added 3×P-BBQ; Added 3×2L-SC; Added 1×2L-OG."
}
```
**Sheet columns updated**
- **P** = 3, **U** = 3, **W** = 1  
- **C/H/J/K** set by app defaults; **D/E/G/Z/AA** left blank

---

### Example C — Location + payment + grams-based sizing
**Message**
```
Hi! 2 x 200g sour cream, 1 x 100g bbq.
For Maria Santos.
Payment via GCash.
sa QC.
delivery 60
discount 10%
```

**LLM JSON**
```json
{
  "customer_name": "Maria Santos",
  "payment_method": "Gcash",
  "customer_location": "Quezon City",
  "discount_percentage": 10.0,
  "discount_amount": 73,
  "shipping_fee": 60,
  "items": [
    {"product_code": "2L-SC", "quantity": 2},
    {"product_code": "P-BBQ", "quantity": 1}
  ],
  "confidence": 0.95,
  "notes": "200g→tub (2L-SC), 100g→pouch (P-BBQ)."
}
```
**Computation notes**
- Items subtotal = 2×290 + 1×150 = **730**  
- `discount_amount` = int(730 × 0.10) = **73**

**Sheet columns updated**
- **D** = Maria Santos
- **E** = Ferdie (auto, from Quezon City)
- **G** = Gcash
- **U** = 2, **P** = 1
- **Z** = 60, **AA** = 73
- **C/H/J/K** set by app

---

## Implementation Tips
- Keep the Anthropic prompt in sync with these rules (enumerations & examples matter).  
- Enforce JSON-only outputs (reject/reprompt if prose sneaks in).  
- When LLM is uncertain, it’s okay to set fields to `null` and leave corresponding columns blank.
