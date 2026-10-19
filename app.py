
from pathlib import Path

import pandas as pd
import streamlit as st

# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"

FINDINGS_FILE = DATA_DIR / "reconciliation_findings.csv"
INVOICES_FILE = DATA_DIR / "uploaded_invoices.csv"
PURCHASE_ORDERS_FILE = DATA_DIR / "uploaded_purchase_orders.csv"
UPLOADED_FINDINGS_FILE = DATA_DIR / "uploaded_reconciliation_findings.csv"


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Intelligent Invoice Auditor",
    page_icon="📊",
    layout="wide",
)

st.title("Intelligent Invoice Reconciliation")

st.write(
    "Upload invoices and approved purchase orders, review "
    "discrepancies, and identify potential payment anomalies."
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def read_uploaded_file(uploaded_file):
    """Read an uploaded CSV or Excel file."""
    if uploaded_file.name.lower().endswith(".csv"):
        return pd.read_csv(uploaded_file)

    return pd.read_excel(uploaded_file)


def validate_columns(dataframe, required_columns):
    """Return a list of required columns that are missing."""
    return sorted(set(required_columns) - set(dataframe.columns))


def normalize_ids(dataframe, id_column):
    """Return normalized IDs for duplicate comparisons."""
    return (
        dataframe[id_column]
        .astype("string")
        .str.strip()
    )


def save_records(
    new_records,
    destination,
    id_column,
    save_mode,
):
    """
    Save records while preventing duplicate IDs.

    Add mode:
        Existing IDs and repeated IDs in the upload are skipped.

    Replace mode:
        Existing records are replaced with the upload, while
        repeated IDs within the upload are skipped.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    records = new_records.copy()

    # Reject missing or blank identifiers.
    ids = normalize_ids(records, id_column)

    if ids.isna().any() or ids.eq("").any():
        raise ValueError(
            f"Every record must have a non-empty {id_column}."
        )

    # Normalize identifiers before saving and comparing.
    records[id_column] = ids

    # Remove repeated IDs inside this upload.
    original_upload_count = len(records)

    records = records.drop_duplicates(
        subset=[id_column],
        keep="first",
    ).copy()

    duplicates_in_upload = original_upload_count - len(records)

    # Replace mode: replace the uploaded dataset.
    if save_mode == "Replace":
        records.to_csv(destination, index=False)

        return {
            "added": len(records),
            "skipped_existing": 0,
            "skipped_upload_duplicates": duplicates_in_upload,
            "total": len(records),
        }

    # Add mode: append only identifiers that do not exist.
    if destination.exists() and destination.stat().st_size > 0:
        existing_records = pd.read_csv(destination)

        if id_column not in existing_records.columns:
            raise ValueError(
                f"The existing file does not contain {id_column}."
            )

        if set(existing_records.columns) != set(records.columns):
            raise ValueError(
                "The uploaded file columns do not match the saved file. "
                "Use the same columns or choose Replace."
            )

        # Keep the existing file's column order.
        records = records[existing_records.columns]

        existing_ids = normalize_ids(existing_records, id_column)
        new_ids = normalize_ids(records, id_column)

        already_exists = new_ids.isin(set(existing_ids.dropna()))

        skipped_existing = int(already_exists.sum())

        records_to_add = records.loc[~already_exists].copy()

        combined_records = pd.concat(
            [existing_records, records_to_add],
            ignore_index=True,
        )

    else:
        existing_records = pd.DataFrame()
        records_to_add = records.copy()
        skipped_existing = 0

        combined_records = records_to_add.copy()

    combined_records.to_csv(destination, index=False)

    return {
        "added": len(records_to_add),
        "skipped_existing": skipped_existing,
        "skipped_upload_duplicates": duplicates_in_upload,
        "total": len(combined_records),
    }


def show_save_summary(result, record_name):
    """Display how many records were saved or skipped."""
    st.success(
        f"Saved {result['added']} new {record_name}. "
        f"Total records stored: {result['total']}."
    )

    if result["skipped_existing"] > 0:
        st.warning(
            f"Skipped {result['skipped_existing']} record(s) "
            "because their IDs already exist."
        )

    if result["skipped_upload_duplicates"] > 0:
        st.warning(
            f"Skipped {result['skipped_upload_duplicates']} "
            "repeated ID(s) within the uploaded file."
        )


# ============================================================
# LOAD ORIGINAL RECONCILIATION FINDINGS
# ============================================================

if not FINDINGS_FILE.exists():
    st.error(
        "Original findings file not found. "
        "Run `python src/reconcile.py` first."
    )
    st.stop()

try:
    findings = pd.read_csv(FINDINGS_FILE)

except Exception as error:
    st.error(f"Could not read the original findings: {error}")
    st.stop()

if findings.empty or "issue_type" not in findings.columns:
    st.error(
        "The original findings file is empty or missing the issue_type column."
    )
    st.stop()


# ============================================================
# PRIORITIES AND EXPLANATIONS
# ============================================================

high_priority = [
    "MISSING_PURCHASE_ORDER",
    "MISSING_OR_UNAPPROVED_PURCHASE_ORDER",
    "DUPLICATE_INVOICE",
    "OVERPAYMENT",
]

medium_priority = [
    "AMOUNT_MISMATCH",
    "VENDOR_MISMATCH",
    "QUANTITY_MISMATCH",
    "PRICE_MISMATCH",
]

issue_explanations = {
    "AMOUNT_MISMATCH":
        "Invoice amount differs from the approved purchase order.",
    "DUPLICATE_INVOICE":
        "The invoice appears more than once in the records.",
    "MISSING_PURCHASE_ORDER":
        "No matching purchase order was found.",
    "MISSING_OR_UNAPPROVED_PURCHASE_ORDER":
        "No matching approved purchase order was found.",
    "VENDOR_MISMATCH":
        "The invoice vendor differs from the purchase order vendor.",
    "QUANTITY_MISMATCH":
        "The invoiced quantity differs from the ordered quantity.",
    "PRICE_MISMATCH":
        "The invoiced unit price differs from the ordered unit price.",
    "OVERPAYMENT":
        "The payment exceeds the invoice amount.",
    "DUPLICATE_PAYMENT":
        "The payment ID appears more than once in the records.",
}

findings["priority"] = findings["issue_type"].map(
    lambda issue: (
        "High" if issue in high_priority
        else "Medium" if issue in medium_priority
        else "Low"
    )
)

findings["explanation"] = findings["issue_type"].map(
    issue_explanations
).fillna("Review this record for an unexpected discrepancy.")


# ============================================================
# SUMMARY METRICS
# ============================================================

st.subheader("Original Dataset Overview")

col1, col2, col3 = st.columns(3)

col1.metric("Flagged Records", len(findings))

if "invoice_id" in findings.columns:
    col2.metric(
        "Affected Invoice IDs",
        findings["invoice_id"].nunique(),
    )
else:
    col2.metric("Affected Invoice IDs", "N/A")

col3.metric(
    "Anomaly Categories",
    findings["issue_type"].nunique(),
)

st.divider()


# ============================================================
# ANOMALY SUMMARY AND CHART
# ============================================================

st.subheader("Findings by Anomaly Type")

issue_summary = (
    findings["issue_type"]
    .value_counts()
    .rename_axis("Anomaly Type")
    .reset_index(name="Flagged Records")
)

st.dataframe(
    issue_summary,
    use_container_width=True,
    hide_index=True,
)

st.subheader("Anomaly Distribution")

st.bar_chart(
    issue_summary.set_index("Anomaly Type"),
    x_label="Anomaly Type",
    y_label="Number of Flagged Records",
)

st.divider()


# ============================================================
# UPLOAD NEW INVOICES
# ============================================================

st.subheader("Upload New Invoices")

st.write(
    "Upload invoice records as CSV or Excel. "
    "Each invoice must have a unique invoice ID."
)

uploaded_file = st.file_uploader(
    "Choose an invoice file",
    type=["csv", "xlsx"],
    key="invoice_upload",
)

if uploaded_file is not None:
    try:
        new_invoices = read_uploaded_file(uploaded_file)

        required_invoice_columns = {
            "invoice_id",
            "vendor_id",
            "po_id",
            "quantity",
            "unit_price",
            "invoice_amount",
        }

        missing_columns = validate_columns(
            new_invoices,
            required_invoice_columns,
        )

        if missing_columns:
            st.error(
                f"Invoice file is missing required columns: "
                f"{missing_columns}"
            )

        elif new_invoices.empty:
            st.warning(
                "The uploaded file contains no invoice records."
            )

        elif (
            new_invoices["invoice_id"].isna().any()
            or new_invoices["invoice_id"]
            .astype("string")
            .str.strip()
            .eq("")
            .any()
        ):
            st.error(
                "Every invoice must have a non-empty invoice_id."
            )

        else:
            st.write("Preview of uploaded invoices")

            st.dataframe(
                new_invoices.head(10),
                use_container_width=True,
                hide_index=True,
            )

            st.success(
                f"Loaded {len(new_invoices)} invoice record(s)."
            )

            invoice_save_mode = st.radio(
                "How should these invoices be saved?",
                [
                    "Add new invoices",
                    "Replace uploaded invoices",
                ],
                key="invoice_save_mode",
            )

            if st.button(
                "Save Invoices",
                key="save_invoices",
                type="primary",
            ):
                try:
                    save_mode = (
                        "Replace"
                        if invoice_save_mode == "Replace uploaded invoices"
                        else "Add"
                    )

                    result = save_records(
                        new_records=new_invoices,
                        destination=INVOICES_FILE,
                        id_column="invoice_id",
                        save_mode=save_mode,
                    )

                    show_save_summary(result, "invoice record(s)")

                except Exception as error:
                    st.error(f"Could not save invoices: {error}")

    except Exception as error:
        st.error(f"Could not read the invoice file: {error}")


st.divider()


# ============================================================
# UPLOAD APPROVED PURCHASE ORDERS
# ============================================================

st.subheader("Upload Approved Purchase Orders")

st.write(
    "Upload purchase orders with their approval status. "
    "Only purchase orders marked Approved should be used "
    "as approved references during reconciliation."
)

uploaded_po_file = st.file_uploader(
    "Choose a purchase-order file",
    type=["csv", "xlsx"],
    key="purchase_order_upload",
)

if uploaded_po_file is not None:
    try:
        new_purchase_orders = read_uploaded_file(uploaded_po_file)

        required_po_columns = {
            "po_id",
            "vendor_id",
            "quantity",
            "unit_price",
            "approved_amount",
            "approval_status",
        }

        missing_columns = validate_columns(
            new_purchase_orders,
            required_po_columns,
        )

        if missing_columns:
            st.error(
                f"Purchase-order file is missing required columns: "
                f"{missing_columns}"
            )

        elif new_purchase_orders.empty:
            st.warning(
                "The uploaded file contains no purchase orders."
            )

        elif (
            new_purchase_orders["po_id"].isna().any()
            or new_purchase_orders["po_id"]
            .astype("string")
            .str.strip()
            .eq("")
            .any()
        ):
            st.error(
                "Every purchase order must have a non-empty po_id."
            )

        else:
            st.write("Preview of uploaded purchase orders")

            st.dataframe(
                new_purchase_orders.head(10),
                use_container_width=True,
                hide_index=True,
            )

            st.success(
                f"Loaded {len(new_purchase_orders)} purchase order(s)."
            )

            po_save_mode = st.radio(
                "How should these purchase orders be saved?",
                [
                    "Add new purchase orders",
                    "Replace uploaded purchase orders",
                ],
                key="po_save_mode",
            )

            if st.button(
                "Save Purchase Orders",
                key="save_purchase_orders",
                type="primary",
            ):
                try:
                    save_mode = (
                        "Replace"
                        if po_save_mode == "Replace uploaded purchase orders"
                        else "Add"
                    )

                    result = save_records(
                        new_records=new_purchase_orders,
                        destination=PURCHASE_ORDERS_FILE,
                        id_column="po_id",
                        save_mode=save_mode,
                    )

                    show_save_summary(
                        result,
                        "purchase order(s)",
                    )

                except Exception as error:
                    st.error(
                        f"Could not save purchase orders: {error}"
                    )

    except Exception as error:
        st.error(
            f"Could not read the purchase-order file: {error}"
        )


# ============================================================
# UPLOADED INVOICE RECONCILIATION RESULTS
# ============================================================

st.divider()

st.subheader("Uploaded Invoice Reconciliation Results")

if not UPLOADED_FINDINGS_FILE.exists():
    st.info(
        "No uploaded reconciliation results are available yet. "
        "Save invoices and purchase orders, then run "
        "`python src/reconcile_uploaded.py` in the VS Code terminal."
    )

elif UPLOADED_FINDINGS_FILE.stat().st_size == 0:
    st.success(
        "No reconciliation anomalies were found in the uploaded invoices."
    )

else:
    try:
        uploaded_findings = pd.read_csv(UPLOADED_FINDINGS_FILE)

        if uploaded_findings.empty:
            st.success(
                "No reconciliation anomalies were found in the uploaded invoices."
            )

        else:
            st.write(
                f"Flagged records: {len(uploaded_findings)}"
            )

            st.dataframe(
                uploaded_findings,
                use_container_width=True,
                hide_index=True,
            )

            st.download_button(
                label="Download uploaded reconciliation results",
                data=uploaded_findings.to_csv(
                    index=False
                ).encode("utf-8"),
                file_name="uploaded_reconciliation_findings.csv",
                mime="text/csv",
                key="download_uploaded_findings",
            )

    except pd.errors.EmptyDataError:
        st.success(
            "No reconciliation anomalies were found in the uploaded invoices."
        )

    except Exception as error:
        st.error(
            f"Could not read uploaded reconciliation results: {error}"
        )


# ============================================================
# EXPLORE ORIGINAL FLAGGED RECORDS
# ============================================================

st.divider()

st.subheader("Explore Flagged Records")

available_issues = sorted(
    findings["issue_type"].dropna().unique()
)

selected_issues = st.multiselect(
    "Filter by anomaly type",
    options=available_issues,
    default=available_issues,
)

filtered_findings = findings[
    findings["issue_type"].isin(selected_issues)
]

selected_priorities = st.multiselect(
    "Filter by priority",
    options=["High", "Medium", "Low"],
    default=["High", "Medium", "Low"],
)

filtered_findings = filtered_findings[
    filtered_findings["priority"].isin(selected_priorities)
]

search_invoice = st.text_input(
    "Search by invoice ID",
    placeholder="Example: INV000100",
)

if search_invoice and "invoice_id" in filtered_findings.columns:
    filtered_findings = filtered_findings[
        filtered_findings["invoice_id"]
        .astype(str)
        .str.contains(
            search_invoice.strip(),
            case=False,
            na=False,
        )
    ]

st.write(
    f"Showing {len(filtered_findings)} flagged records"
)

display_columns = [
    "invoice_id",
    "vendor_id",
    "po_id",
    "issue_type",
    "priority",
    "explanation",
    "invoice_amount",
    "approved_amount",
    "payment_amount",
    "overpayment_amount",
]

available_columns = [
    column
    for column in display_columns
    if column in filtered_findings.columns
]

column_config = {
    "explanation": st.column_config.TextColumn(
        "Why Was It Flagged?",
        help="Explains why the reconciliation system flagged this record.",
        width="large",
    ),
    "invoice_amount": st.column_config.NumberColumn(
        "Invoice Amount",
        format="%.2f",
    ),
    "approved_amount": st.column_config.NumberColumn(
        "Approved Amount",
        format="%.2f",
    ),
    "payment_amount": st.column_config.NumberColumn(
        "Payment Amount",
        format="%.2f",
    ),
    "overpayment_amount": st.column_config.NumberColumn(
        "Overpayment Amount",
        format="%.2f",
    ),
}

st.dataframe(
    filtered_findings[available_columns],
    use_container_width=True,
    hide_index=True,
    column_config=column_config,
)

st.download_button(
    label="Download filtered findings as CSV",
    data=filtered_findings.to_csv(
        index=False
    ).encode("utf-8"),
    file_name="filtered_reconciliation_findings.csv",
    mime="text/csv",
    key="download_original_findings",
)

st.caption(
    "Alerts indicate records that need review; they do not prove fraud. "
    "Verify every flagged record before taking financial action."
)
