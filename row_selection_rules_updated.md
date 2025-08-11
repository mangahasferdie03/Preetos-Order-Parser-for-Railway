# Preetos.ai – Row Selection Rules & Column Mapping for Order Insertion

## Objective
This document defines the rules and column mappings for how the Telegram bot (or Streamlit web app) should parse customer orders and insert them into Google Sheets.  
The goal is to ensure that:
- Orders are **always placed in the correct row** (first truly empty row according to our rule).
- Data is **mapped consistently** into the correct Google Sheet columns.

---

## Envisioned Bot Flow
1. **User sends a customer message** to the Telegram bot.  
   This message may contain:
   - Customer name
   - Product orders
   - Payment method
   - Location
   - Discount information
   - Shipping fee

2. **The bot parses the message** using Claude AI (with a regex-based fallback) to extract the structured order data.

3. **The bot maps the extracted fields** to the correct Google Sheets columns as per our defined mapping.

4. **The bot finds the next available row** in the `ORDER` worksheet following the Row Selection Rule.

5. **The bot updates the Google Sheet** with the parsed order details.

---

## Row Selection Rule
When inserting a new order, the bot must **always choose the first truly empty row** where:
- **Column D (Customer Name)** is empty **AND**
- **All product quantity columns (N, O, P, Q, T, U, V, W)** are empty or contain `"0"`.

This prevents overwriting existing orders while ensuring that blank rows are reused properly.

### Optimized Approach
1. Fetch **only the relevant columns**:
   - Customer Name → Column **D**
   - Product Quantities → Columns **N, O, P, Q, T, U, V, W**
2. Start checking from **row 2** (skip header row).
3. For each row:
   - If Column D is empty **AND** all product columns are empty or `"0"`, select this row for the new order.
   - Stop immediately when the first valid row is found.

---

## Column Mapping
The bot supports updating the following columns:

| Column | Purpose | Mapping in Code |
|--------|---------|-----------------|
| **C**  | Order Date | `updates['C']` |
| **D**  | Customer Name | `updates['D']` |
| **E**  | Sold By (auto-assigned based on location) | `updates['E']` |
| **G**  | Payment Method | `updates['G']` |
| **H**  | Payment Status (always `"Unpaid"`) | `updates['H']` |
| **J**  | Notes (🤖 + timestamp) | `updates['J']` |
| **K**  | Order Type (always `"Reserved"`) | `updates['K']` |
| **N**  | Pouch – Cheese (`P-CHZ`) | `updates['N']` |
| **O**  | Pouch – Sour Cream (`P-SC`) | `updates['O']` |
| **P**  | Pouch – BBQ (`P-BBQ`) | `updates['P']` |
| **Q**  | Pouch – Original Blend (`P-OG`) | `updates['Q']` |
| **T**  | Tub – Cheese (`2L-CHZ`) | `updates['T']` |
| **U**  | Tub – Sour Cream (`2L-SC`) | `updates['U']` |
| **V**  | Tub – BBQ (`2L-BBQ`) | `updates['V']` |
| **W**  | Tub – Original Spice Blend (`2L-OG`) | `updates['W']` |
| **Z**  | Shipping Fee | `updates['Z']` |
| **AA** | Discount Amount | `updates['AA']` |

---

## Summary
**Rule:**  
> Select the first row where Column D and all product columns (N, O, P, Q, T, U, V, W) are empty or `"0"`.  
> Then populate it according to the column mapping above.

**Flow:**  
> Telegram message → Bot parses message → Bot maps fields to columns → Bot finds next available row → Bot updates Google Sheet.

