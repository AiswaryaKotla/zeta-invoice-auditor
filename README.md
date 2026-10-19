# Intelligent Invoice Reconciliation & Anomaly Detection System

## Project Overview

The Intelligent Invoice Reconciliation & Anomaly Detection System identifies discrepancies between invoices, approved purchase orders, and payment records. It helps users identify potential billing errors and unusual payment activity through automated rule-based reconciliation and an interactive dashboard.

The project supports both reconciliation of the generated sample dataset and reconciliation of user-uploaded invoices against approved purchase orders.

## Objectives

- Identify invoice amount mismatches.
- Detect duplicate invoice records.
- Find invoices without matching or approved purchase orders.
- Identify vendor, quantity, and unit-price mismatches.
- Detect payments that exceed invoice amounts.
- Validate uploaded invoice and purchase-order files.
- Present findings through an interactive dashboard and downloadable reports.

## Technologies Used

- **Python** — Core programming language.
- **Pandas** — Data processing, validation, and reconciliation.
- **Streamlit** — Interactive dashboard and file-upload interface.
- **Plotly / Streamlit charts** — Data visualization technologies available for the project.
- **CSV** — Storage for synthetic business records and reconciliation results.
- **Scikit-learn** — Installed for potential future machine-learning enhancements.
- **SQLite** — Installed for potential future database integration.

## Key Features

- Automated invoice and purchase-order validation.
- Detection of discrepancies using rule-based checks.
- Detection of missing required values in uploaded records.
- Identification of missing or unapproved purchase orders.
- Detection of amount, vendor, quantity, and unit-price mismatches.
- Duplicate invoice ID handling during invoice uploads.
- Dashboard summary metrics and anomaly distribution chart.
- Filtering by anomaly type and review priority.
- Invoice ID search.
- Downloadable CSV reports.
- Separate reconciliation results for uploaded invoices.
- Explanations describing why records were flagged.

## Dataset

The project uses synthetic business records generated for demonstration and testing.

The generated dataset includes:

- Vendors
- Purchase orders
- Invoices
- Payments
- Expected findings for evaluation

Uploaded invoice and purchase-order files are stored separately from the original generated datasets.

## Project Structure

```text
ZetaInvoiceAuditor/
├── data/
│   ├── vendors.csv
│   ├── purchase_orders.csv
│   ├── invoices.csv
│   ├── payments.csv
│   ├── expected_findings.csv
│   ├── reconciliation_findings.csv
│   ├── uploaded_invoices.csv
│   ├── uploaded_purchase_orders.csv
│   └── uploaded_reconciliation_findings.csv
├── src/
│   ├── generate_data.py
│   ├── reconcile.py
│   └── reconcile_uploaded.py
├── app.py
├── requirements.txt
└── README.md
```

## How to Run

### 1. Open the project

Open the `ZetaInvoiceAuditor` folder in Visual Studio Code.

### 2. Activate the virtual environment

In the VS Code PowerShell terminal, run:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Generate the sample dataset

```powershell
python src/generate_data.py
```

### 4. Run reconciliation on the generated dataset

```powershell
python src/reconcile.py
```

This generates the reconciliation findings used by the dashboard.

### 5. Start the dashboard

```powershell
streamlit run app.py
```

Open the local URL displayed in the terminal, usually `http://localhost:8501`.

### 6. Reconcile uploaded invoices

Upload and save invoice and purchase-order CSV or Excel files through the dashboard. Ensure the purchase-order file contains the required columns, including `approval_status`.

Then run:

```powershell
python src/reconcile_uploaded.py
```

The script validates the uploaded datasets, checks invoices against approved purchase orders, and saves the findings to `data/uploaded_reconciliation_findings.csv`.

## Testing

The project has been tested with sample scenarios including:

- Invoice amount mismatches.
- Missing or unapproved purchase orders.
- Vendor mismatches.
- Quantity mismatches.
- Unit-price mismatches.
- Missing required invoice values.
- Invalid invoice uploads with missing required columns.
- Clean invoices matching approved purchase orders.
- Repeated invoice uploads with existing invoice IDs.

A clean-invoice test produced zero flagged records, and an invalid upload was rejected because required columns were missing.

## Important Note

The system uses rule-based checks to flag records for human review. An alert indicates a potential discrepancy and does not establish fraud or wrongdoing.

The uploaded-invoice reconciliation process currently checks invoice details against approved purchase orders. Payment-related checks are part of the generated-dataset reconciliation workflow.

## Future Enhancements

- Machine-learning-based anomaly scoring.
- SQLite database integration.
- More detailed reports and evaluation metrics.
- Additional validation and error-handling tests.
- Improved dashboard visualizations and explanations.
```
