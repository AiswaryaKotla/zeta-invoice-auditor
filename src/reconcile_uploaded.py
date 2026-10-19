
from pathlib import Path

import pandas as pd

# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

INVOICES_FILE = DATA_DIR / "uploaded_invoices.csv"
PURCHASE_ORDERS_FILE = DATA_DIR / "uploaded_purchase_orders.csv"
UPLOADED_FINDINGS_FILE = DATA_DIR / "uploaded_reconciliation_findings.csv"


# --------------------------------------------------
# LOAD DATASETS
# --------------------------------------------------

def load_uploaded_datasets():
    """Load uploaded invoices and purchase orders."""

    if not INVOICES_FILE.exists():
        raise FileNotFoundError(
            "Uploaded invoices not found. Upload and save invoices first."
        )

    if not PURCHASE_ORDERS_FILE.exists():
        raise FileNotFoundError(
            "Uploaded purchase orders not found. Upload and save purchase orders first."
        )

    invoices = pd.read_csv(INVOICES_FILE)
    purchase_orders = pd.read_csv(PURCHASE_ORDERS_FILE)

    return invoices, purchase_orders


# --------------------------------------------------
# VALIDATE DATASETS
# --------------------------------------------------

def validate_uploaded_datasets(invoices, purchase_orders):
    """Validate required columns, empty datasets and missing values."""

    required_invoice_columns = [
        "invoice_id",
        "vendor_id",
        "po_id",
        "quantity",
        "unit_price",
        "invoice_amount",
    ]

    required_po_columns = [
        "po_id",
        "vendor_id",
        "quantity",
        "unit_price",
        "approved_amount",
        "approval_status",
    ]

    missing_invoice_columns = (
        set(required_invoice_columns) - set(invoices.columns)
    )

    missing_po_columns = (
        set(required_po_columns) - set(purchase_orders.columns)
    )

    if missing_invoice_columns:
        raise ValueError(
            "Invoice file is missing columns: "
            f"{sorted(missing_invoice_columns)}"
        )

    if missing_po_columns:
        raise ValueError(
            "Purchase-order file is missing columns: "
            f"{sorted(missing_po_columns)}"
        )

    if invoices.empty:
        raise ValueError("The invoice file contains no records.")

    if purchase_orders.empty:
        raise ValueError("The purchase-order file contains no records.")

    print("Dataset structure validation successful.")


# --------------------------------------------------
# HELPER: FIND INVALID VALUES
# --------------------------------------------------

def detect_invalid_values(dataframe, required_columns, dataset_name):
    """Report records with missing required values or invalid numbers."""

    findings = []

    numeric_columns = {
        "quantity",
        "unit_price",
        "invoice_amount",
        "approved_amount",
    }

    for column in required_columns:
        missing_mask = (
            dataframe[column].isna()
            | dataframe[column].astype(str).str.strip().eq("")
        )

        for index in dataframe.index[missing_mask]:
            findings.append({
                "source_dataset": dataset_name,
                "source_row": int(index) + 2,
                "column_name": column,
                "issue_type": "MISSING_REQUIRED_VALUE",
                "details": f"Required value '{column}' is missing.",
            })

        if column in numeric_columns:
            numeric_values = pd.to_numeric(
                dataframe[column],
                errors="coerce",
            )

            invalid_mask = (
                ~missing_mask
                & (
                    numeric_values.isna()
                    | ~numeric_values.map(
                        lambda value: (
                            pd.notna(value)
                            and abs(value) != float("inf")
                        )
                    )
                )
            )

            for index in dataframe.index[invalid_mask]:
                findings.append({
                    "source_dataset": dataset_name,
                    "source_row": int(index) + 2,
                    "column_name": column,
                    "issue_type": "INVALID_NUMERIC_VALUE",
                    "details": (
                        f"Column '{column}' must contain a valid finite number."
                    ),
                })

    return pd.DataFrame(findings)


# --------------------------------------------------
# PREPARE DATA
# --------------------------------------------------

def prepare_uploaded_datasets(invoices, purchase_orders):
    """Standardize IDs and convert numeric fields."""

    invoices = invoices.copy()
    purchase_orders = purchase_orders.copy()

    id_columns = ["invoice_id", "vendor_id", "po_id"]

    for column in id_columns:
        invoices[column] = (
            invoices[column].astype("string").str.strip()
        )

    for column in ["vendor_id", "po_id"]:
        purchase_orders[column] = (
            purchase_orders[column].astype("string").str.strip()
        )

    invoice_numeric_columns = [
        "quantity",
        "unit_price",
        "invoice_amount",
    ]

    po_numeric_columns = [
        "quantity",
        "unit_price",
        "approved_amount",
    ]

    for column in invoice_numeric_columns:
        invoices[column] = pd.to_numeric(
            invoices[column],
            errors="coerce",
        )

    for column in po_numeric_columns:
        purchase_orders[column] = pd.to_numeric(
            purchase_orders[column],
            errors="coerce",
        )

    purchase_orders["approval_status"] = (
        purchase_orders["approval_status"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    return invoices, purchase_orders


# --------------------------------------------------
# DUPLICATE INVOICE DETECTION
# --------------------------------------------------

def detect_duplicate_invoices(invoices):
    """Flag every row whose invoice ID appears more than once."""

    duplicate_mask = (
        invoices["invoice_id"].notna()
        & invoices["invoice_id"].ne("")
        & invoices.duplicated(
            subset=["invoice_id"],
            keep=False,
        )
    )

    duplicates = invoices[duplicate_mask].copy()

    if not duplicates.empty:
        duplicates["issue_type"] = "DUPLICATE_INVOICE"
        duplicates["details"] = (
            "This invoice ID appears more than once in the uploaded data."
        )

    return duplicates


# --------------------------------------------------
# APPROVED PURCHASE ORDERS
# --------------------------------------------------

def get_approved_purchase_orders(purchase_orders):
    """Return approved POs and reject ambiguous approved PO IDs."""

    approved_orders = purchase_orders[
        purchase_orders["approval_status"].eq("approved")
    ].copy()

    if approved_orders.empty:
        raise ValueError("No approved purchase orders were found.")

    valid_po_ids = (
        approved_orders["po_id"].notna()
        & approved_orders["po_id"].ne("")
    )

    duplicate_po_ids = approved_orders[
        valid_po_ids
        & approved_orders.duplicated(
            subset=["po_id"],
            keep=False,
        )
    ]

    if not duplicate_po_ids.empty:
        duplicate_ids = (
            duplicate_po_ids["po_id"].dropna().unique().tolist()
        )

        raise ValueError(
            "Duplicate approved PO IDs found. Resolve these before "
            f"reconciliation: {duplicate_ids}"
        )

    print(f"Approved purchase orders found: {len(approved_orders)}")

    return approved_orders


# --------------------------------------------------
# AMOUNT MISMATCH AND MISSING PO DETECTION
# --------------------------------------------------

def detect_uploaded_amount_mismatches(invoices, approved_orders):
    """Detect amount mismatches and missing or unapproved POs."""

    merged = invoices.merge(
        approved_orders[["po_id", "approved_amount"]],
        on="po_id",
        how="left",
        indicator=True,
        validate="many_to_one",
    )

    missing_orders = merged[
        merged["_merge"].eq("left_only")
    ].copy()

    if not missing_orders.empty:
        missing_orders["issue_type"] = (
            "MISSING_OR_UNAPPROVED_PURCHASE_ORDER"
        )
        missing_orders["details"] = (
            "No matching approved purchase order was found."
        )

    matched = merged[
        merged["_merge"].eq("both")
    ].copy()

    valid_amounts = (
        matched["invoice_amount"].notna()
        & matched["approved_amount"].notna()
    )

    amount_mismatches = matched[
        valid_amounts
        & (
            matched["invoice_amount"].round(2)
            != matched["approved_amount"].round(2)
        )
    ].copy()

    if not amount_mismatches.empty:
        amount_mismatches["issue_type"] = "AMOUNT_MISMATCH"
        amount_mismatches["details"] = (
            "Invoice amount differs from the approved PO amount."
        )

    print(f"Amount mismatches found: {len(amount_mismatches)}")
    print(f"Missing or unapproved POs found: {len(missing_orders)}")

    return amount_mismatches, missing_orders


# --------------------------------------------------
# VENDOR MISMATCH
# --------------------------------------------------

def detect_uploaded_vendor_mismatches(invoices, approved_orders):
    """Detect vendor IDs that differ from the approved PO vendor."""

    merged = invoices.merge(
        approved_orders[["po_id", "vendor_id"]].rename(
            columns={"vendor_id": "po_vendor_id"}
        ),
        on="po_id",
        how="inner",
        validate="many_to_one",
    )

    valid_ids = (
        merged["vendor_id"].notna()
        & merged["po_vendor_id"].notna()
    )

    mismatches = merged[
        valid_ids
        & (
            merged["vendor_id"].astype(str).str.strip()
            != merged["po_vendor_id"].astype(str).str.strip()
        )
    ].copy()

    if not mismatches.empty:
        mismatches["issue_type"] = "VENDOR_MISMATCH"
        mismatches["details"] = (
            "Invoice vendor differs from the approved PO vendor."
        )

    return mismatches


# --------------------------------------------------
# QUANTITY MISMATCH
# --------------------------------------------------

def detect_uploaded_quantity_mismatches(invoices, approved_orders):
    """Detect differences between invoice and approved PO quantities."""

    merged = invoices.merge(
        approved_orders[["po_id", "quantity"]].rename(
            columns={"quantity": "po_quantity"}
        ),
        on="po_id",
        how="inner",
        validate="many_to_one",
    )

    valid_quantities = (
        merged["quantity"].notna()
        & merged["po_quantity"].notna()
    )

    mismatches = merged[
        valid_quantities
        & (
            merged["quantity"]
            != merged["po_quantity"]
        )
    ].copy()

    if not mismatches.empty:
        mismatches["issue_type"] = "QUANTITY_MISMATCH"
        mismatches["details"] = (
            "Invoice quantity differs from the approved PO quantity."
        )

    return mismatches


# --------------------------------------------------
# PRICE MISMATCH
# --------------------------------------------------

def detect_uploaded_price_mismatches(invoices, approved_orders):
    """Detect differences between invoice and approved PO unit prices."""

    merged = invoices.merge(
        approved_orders[["po_id", "unit_price"]].rename(
            columns={"unit_price": "po_unit_price"}
        ),
        on="po_id",
        how="inner",
        validate="many_to_one",
    )

    valid_prices = (
        merged["unit_price"].notna()
        & merged["po_unit_price"].notna()
    )

    mismatches = merged[
        valid_prices
        & (
            merged["unit_price"].round(2)
            != merged["po_unit_price"].round(2)
        )
    ].copy()

    if not mismatches.empty:
        mismatches["issue_type"] = "PRICE_MISMATCH"
        mismatches["details"] = (
            "Invoice unit price differs from the approved PO unit price."
        )

    return mismatches


# --------------------------------------------------
# COMBINE FINDINGS
# --------------------------------------------------

def combine_uploaded_findings(*finding_dataframes):
    """Combine findings into a single results table."""

    non_empty_findings = [
        dataframe
        for dataframe in finding_dataframes
        if dataframe is not None and not dataframe.empty
    ]

    if not non_empty_findings:
        return pd.DataFrame(
            columns=["issue_type", "details"]
        )

    return pd.concat(
        non_empty_findings,
        ignore_index=True,
        sort=False,
    )


# --------------------------------------------------
# SAVE FINDINGS
# --------------------------------------------------

def save_uploaded_findings(findings):
    """Save results without leaving stale findings from an earlier run."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    findings.to_csv(
        UPLOADED_FINDINGS_FILE,
        index=False,
    )

    print(f"Findings saved to: {UPLOADED_FINDINGS_FILE}")
    print(f"Total flagged records: {len(findings)}")


# --------------------------------------------------
# RUN RECONCILIATION
# --------------------------------------------------

def run_uploaded_reconciliation():
    """Run validation and reconciliation on uploaded datasets."""

    invoices, purchase_orders = load_uploaded_datasets()

    validate_uploaded_datasets(
        invoices,
        purchase_orders,
    )

    invoices, purchase_orders = prepare_uploaded_datasets(
        invoices,
        purchase_orders,
    )

    required_invoice_columns = [
        "invoice_id",
        "vendor_id",
        "po_id",
        "quantity",
        "unit_price",
        "invoice_amount",
    ]

    required_po_columns = [
        "po_id",
        "vendor_id",
        "quantity",
        "unit_price",
        "approved_amount",
        "approval_status",
    ]

    invalid_invoice_values = detect_invalid_values(
        invoices,
        required_invoice_columns,
        "invoices",
    )

    invalid_po_values = detect_invalid_values(
        purchase_orders,
        required_po_columns,
        "purchase_orders",
    )

    duplicate_invoices = detect_duplicate_invoices(invoices)

    # Exclude rows with missing key IDs from joins to avoid
    # unreliable matching of missing identifiers.
    valid_invoice_rows = invoices[
        invoices["invoice_id"].notna()
        & invoices["invoice_id"].ne("")
        & invoices["vendor_id"].notna()
        & invoices["vendor_id"].ne("")
        & invoices["po_id"].notna()
        & invoices["po_id"].ne("")
    ].copy()

    valid_po_rows = purchase_orders[
        purchase_orders["po_id"].notna()
        & purchase_orders["po_id"].ne("")
    ].copy()

    approved_orders = get_approved_purchase_orders(
        valid_po_rows
    )

    amount_mismatches, missing_orders = (
        detect_uploaded_amount_mismatches(
            valid_invoice_rows,
            approved_orders,
        )
    )

    vendor_mismatches = detect_uploaded_vendor_mismatches(
        valid_invoice_rows,
        approved_orders,
    )

    quantity_mismatches = detect_uploaded_quantity_mismatches(
        valid_invoice_rows,
        approved_orders,
    )

    price_mismatches = detect_uploaded_price_mismatches(
        valid_invoice_rows,
        approved_orders,
    )

    all_findings = combine_uploaded_findings(
        invalid_invoice_values,
        invalid_po_values,
        duplicate_invoices,
        amount_mismatches,
        missing_orders,
        vendor_mismatches,
        quantity_mismatches,
        price_mismatches,
    )

    save_uploaded_findings(all_findings)

    if all_findings.empty:
        print("No reconciliation anomalies found.")
    else:
        print("\nFindings by issue type:")
        print(all_findings["issue_type"].value_counts())

    return all_findings


# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":
    try:
        run_uploaded_reconciliation()
    except (FileNotFoundError, ValueError) as error:
        print(f"Reconciliation could not run: {error}")
