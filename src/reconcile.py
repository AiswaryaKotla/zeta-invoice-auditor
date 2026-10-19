
from pathlib import Path

import pandas as pd

# Find the project and data folders.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def load_datasets():
    """Load the CSV files needed for invoice reconciliation."""
    vendors = pd.read_csv(DATA_DIR / "vendors.csv")
    purchase_orders = pd.read_csv(DATA_DIR / "purchase_orders.csv")
    invoices = pd.read_csv(DATA_DIR / "invoices.csv")
    payments = pd.read_csv(DATA_DIR / "payments.csv")

    return vendors, purchase_orders, invoices, payments


def validate_datasets(vendors, purchase_orders, invoices, payments):
    """Check whether the required columns are available."""
    required_columns = {
        "vendors": (vendors, ["vendor_id", "vendor_name"]),
        "purchase_orders": (
            purchase_orders,
            ["po_id", "vendor_id", "approved_amount"],
        ),
        "invoices": (
            invoices,
            ["invoice_id", "vendor_id", "po_id", "invoice_amount"],
        ),
        "payments": (
            payments,
            ["payment_id", "invoice_id", "payment_amount"],
        ),
    }

    for name, (dataframe, columns) in required_columns.items():
        missing = set(columns) - set(dataframe.columns)

        if missing:
            raise ValueError(
                f"{name} is missing required columns: {sorted(missing)}"
            )

    print("Dataset validation successful!")


def detect_amount_mismatches(purchase_orders, invoices):
    """Find invoices whose amounts differ from approved purchase orders."""
    merged = invoices.merge(
        purchase_orders[["po_id", "approved_amount"]],
        on="po_id",
        how="left",
        indicator=True,
    )

    mismatches = merged[
        (merged["_merge"] == "both")
        & (merged["invoice_amount"] != merged["approved_amount"])
    ].copy()

    mismatches["issue_type"] = "AMOUNT_MISMATCH"

    return mismatches


def detect_missing_purchase_orders(purchase_orders, invoices):
    """Find invoices that reference nonexistent purchase orders."""
    merged = invoices.merge(
        purchase_orders[["po_id"]],
        on="po_id",
        how="left",
        indicator=True,
    )

    missing_orders = merged[
        merged["_merge"] == "left_only"
    ].copy()

    missing_orders["issue_type"] = "MISSING_PURCHASE_ORDER"

    return missing_orders


def detect_duplicate_invoices(invoices):
    """Find invoice IDs that occur more than once."""
    duplicate_mask = invoices.duplicated(
        subset=["invoice_id"],
        keep=False,
    )

    duplicates = invoices[duplicate_mask].copy()
    duplicates["issue_type"] = "DUPLICATE_INVOICE"

    return duplicates


def detect_vendor_mismatches(purchase_orders, invoices):
    """Find invoices whose vendor differs from the purchase order vendor."""
    merged = invoices.merge(
        purchase_orders[["po_id", "vendor_id"]].rename(
            columns={"vendor_id": "po_vendor_id"}
        ),
        on="po_id",
        how="inner",
    )

    mismatches = merged[
        merged["vendor_id"] != merged["po_vendor_id"]
    ].copy()

    mismatches["issue_type"] = "VENDOR_MISMATCH"

    return mismatches


def detect_quantity_mismatches(purchase_orders, invoices):
    """Find invoices with quantities different from purchase orders."""
    merged = invoices.merge(
        purchase_orders[["po_id", "quantity"]].rename(
            columns={"quantity": "po_quantity"}
        ),
        on="po_id",
        how="inner",
    )

    mismatches = merged[
        merged["quantity"] != merged["po_quantity"]
    ].copy()

    mismatches["issue_type"] = "QUANTITY_MISMATCH"

    return mismatches


def detect_price_mismatches(purchase_orders, invoices):
    """Find invoices with unit prices different from purchase orders."""
    merged = invoices.merge(
        purchase_orders[["po_id", "unit_price"]].rename(
            columns={"unit_price": "po_unit_price"}
        ),
        on="po_id",
        how="inner",
    )

    mismatches = merged[
        merged["unit_price"] != merged["po_unit_price"]
    ].copy()

    mismatches["issue_type"] = "PRICE_MISMATCH"

    return mismatches


def detect_overpayments(invoices, payments):
    """Find payments that exceed the corresponding invoice amount."""
    merged = payments.merge(
        invoices[["invoice_id", "invoice_amount"]],
        on="invoice_id",
        how="inner",
    )

    overpayments = merged[
        merged["payment_amount"] > merged["invoice_amount"]
    ].copy()

    overpayments["overpayment_amount"] = (
        overpayments["payment_amount"]
        - overpayments["invoice_amount"]
    )

    overpayments["issue_type"] = "OVERPAYMENT"

    return overpayments


def detect_duplicate_payments(payments):
    """Find repeated payment IDs."""
    duplicate_mask = payments.duplicated(
        subset=["payment_id"],
        keep=False,
    )

    duplicates = payments[duplicate_mask].copy()
    duplicates["issue_type"] = "DUPLICATE_PAYMENT"

    return duplicates


def combine_findings(*finding_dataframes):
    """Combine anomaly results into one table."""
    non_empty_findings = [
        dataframe
        for dataframe in finding_dataframes
        if not dataframe.empty
    ]

    if not non_empty_findings:
        return pd.DataFrame()

    combined = pd.concat(
        non_empty_findings,
        ignore_index=True,
        sort=False,
    )

    return combined









if __name__ == "__main__":
    # Load the datasets.
    vendors, purchase_orders, invoices, payments = load_datasets()

    # Validate the datasets.
    validate_datasets(
        vendors,
        purchase_orders,
        invoices,
        payments,
    )

    # Detect invoice amount mismatches.
    mismatches = detect_amount_mismatches(
        purchase_orders,
        invoices,
    )

    print(f"\nAmount mismatches found: {len(mismatches)}")

    print(
        mismatches[
            [
                "invoice_id",
                "po_id",
                "invoice_amount",
                "approved_amount",
            ]
        ].head(10)
    )

        # Detect invoices referencing missing purchase orders.
    missing_orders = detect_missing_purchase_orders(
        purchase_orders,
        invoices,
    )

    print(f"\nMissing purchase orders found: {len(missing_orders)}")

    print(
        missing_orders[
            ["invoice_id", "po_id", "invoice_amount"]
        ].head(10)
    )

    
    # Detect duplicate invoices.
    duplicates = detect_duplicate_invoices(invoices)

    print(f"\nDuplicate invoice records found: {len(duplicates)}")

    print(
        duplicates[
            ["invoice_id", "vendor_id", "po_id", "invoice_amount"]
        ].head(10)
    )

    
    # Detect vendor mismatches.
    vendor_mismatches = detect_vendor_mismatches(
        purchase_orders,
        invoices,
    )

    print(f"\nVendor mismatches found: {len(vendor_mismatches)}")

    print(
        vendor_mismatches[
            ["invoice_id", "po_id", "vendor_id", "po_vendor_id"]
        ].head(10)
    )

    
    # Detect quantity mismatches.
    quantity_mismatches = detect_quantity_mismatches(
        purchase_orders,
        invoices,
    )

    print(
        f"\nQuantity mismatches found: {len(quantity_mismatches)}"
    )

    print(
        quantity_mismatches[
            ["invoice_id", "po_id", "quantity", "po_quantity"]
        ].head(10)
    )

    
    # Detect unit-price mismatches.
    price_mismatches = detect_price_mismatches(
        purchase_orders,
        invoices,
    )

    print(f"\nUnit-price mismatches found: {len(price_mismatches)}")

    print(
        price_mismatches[
            ["invoice_id", "po_id", "unit_price", "po_unit_price"]
        ].head(10)
    )

    
    # Detect overpayments.
    overpayments = detect_overpayments(invoices, payments)

    print(f"\nOverpayments found: {len(overpayments)}")

    print(
        overpayments[
            [
                "payment_id",
                "invoice_id",
                "payment_amount",
                "invoice_amount",
                "overpayment_amount",
            ]
        ].head(10)
    )

    
    # Detect duplicate payments.
    duplicate_payments = detect_duplicate_payments(payments)

    print(f"\nDuplicate payment records found: {len(duplicate_payments)}")

    print(
        duplicate_payments[
            ["payment_id", "invoice_id", "payment_amount"]
        ].head(10)
    )

    
    # Combine all detection results.
    all_findings = combine_findings(
        mismatches,
        missing_orders,
        duplicates,
        vendor_mismatches,
        quantity_mismatches,
        price_mismatches,
        overpayments,
        duplicate_payments,
    )

    print(f"\nTotal flagged records: {len(all_findings)}")
    print("\nFindings by issue type:")
    print(all_findings["issue_type"].value_counts())

    # Save the combined results.
    output_path = DATA_DIR / "reconciliation_findings.csv"
    all_findings.to_csv(output_path, index=False)

    print(f"\nCombined findings saved to: {output_path}")



    # Display dataset sizes.
    print(f"\nVendors loaded: {len(vendors)}")
    print(f"Purchase orders loaded: {len(purchase_orders)}")
    print(f"Invoices loaded: {len(invoices)}")
    print(f"Payments loaded: {len(payments)}")
