
from pathlib import Path

import pandas as pd

# Keep the dataset reproducible every time we run this script.
SEED = 42

# Project folders
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Generate the synthetic business records.
vendors = pd.DataFrame(
    [
        {
            "vendor_id": f"V{i:03d}",
            "vendor_name": f"Vendor {i:03d}",
            "category": ["IT Equipment", "Office Supplies", "Services"][
                (i - 1) % 3
            ],
            "status": "Active",
        }
        for i in range(1, 51)
    ]
)

orders = []
invoices = []
payments = []
findings = []

for i in range(1, 1001):
    vendor_number = ((i - 1) % 50) + 1
    vendor_id = f"V{vendor_number:03d}"
    po_id = f"PO{i:05d}"
    invoice_id = f"INV{i:05d}"

    quantity = (i % 10) + 1
    unit_price = 1000 + ((i * 137) % 9000)
    order_amount = quantity * unit_price

    orders.append(
        {
            "po_id": po_id,
            "vendor_id": vendor_id,
            "order_date": f"2026-{((i - 1) % 12) + 1:02d}-05",
            "quantity": quantity,
            "unit_price": unit_price,
            "approved_amount": order_amount,
            "status": "Approved",
        }
    )

    invoice_amount = order_amount
    invoice_quantity = quantity
    invoice_unit_price = unit_price
    invoice_vendor = vendor_id
    invoice_po = po_id
    invoice_date = f"2026-{((i - 1) % 12) + 1:02d}-10"
    issue_type = "NONE"

    # Inject controlled test cases.
    if i % 100 == 0:
        invoice_amount += 2000
        issue_type = "AMOUNT_MISMATCH"

    elif i % 100 == 1:
        invoice_quantity += 1
        invoice_amount = invoice_quantity * invoice_unit_price
        issue_type = "QUANTITY_MISMATCH"

    elif i % 100 == 2:
        invoice_unit_price += 500
        invoice_amount = invoice_quantity * invoice_unit_price
        issue_type = "PRICE_MISMATCH"

    elif i % 100 == 3:
        invoice_vendor = f"V{((vendor_number) % 50) + 1:03d}"
        issue_type = "VENDOR_MISMATCH"

    elif i % 100 == 4:
        invoice_po = "PO99999"
        issue_type = "MISSING_PURCHASE_ORDER"

    invoices.append(
        {
            "invoice_id": invoice_id,
            "vendor_id": invoice_vendor,
            "po_id": invoice_po,
            "invoice_date": invoice_date,
            "quantity": invoice_quantity,
            "unit_price": invoice_unit_price,
            "invoice_amount": invoice_amount,
        }
    )

    # Every 50th invoice is intentionally repeated.
    if i % 50 == 0:
        invoices.append(
            {
                "invoice_id": invoice_id,
                "vendor_id": invoice_vendor,
                "po_id": invoice_po,
                "invoice_date": invoice_date,
                "quantity": invoice_quantity,
                "unit_price": invoice_unit_price,
                "invoice_amount": invoice_amount,
            }
        )
        issue_type = "DUPLICATE_INVOICE"

    # Create payment records for most invoices.
    if i % 20 != 0:
        payment_amount = invoice_amount
        payment_status = "Completed"

        if i % 100 == 5:
            payment_amount += 1500
            issue_type = "OVERPAYMENT"

        payments.append(
            {
                "payment_id": f"PAY{i:05d}",
                "invoice_id": invoice_id,
                "payment_date": f"2026-{((i - 1) % 12) + 1:02d}-15",
                "payment_amount": payment_amount,
                "payment_status": payment_status,
            }
        )

    findings.append(
        {
            "invoice_id": invoice_id,
            "expected_issue": issue_type,
        }
    )

# Save the generated files.
datasets = {
    "vendors.csv": pd.DataFrame(vendors),
    "purchase_orders.csv": pd.DataFrame(orders),
    "invoices.csv": pd.DataFrame(invoices),
    "payments.csv": pd.DataFrame(payments),
    "expected_findings.csv": pd.DataFrame(findings),
}

for filename, dataframe in datasets.items():
    dataframe.to_csv(DATA_DIR / filename, index=False)
    print(f"Created {filename}: {len(dataframe)} rows")

print("\nDataset generation completed.")
print(f"Data folder: {DATA_DIR}")