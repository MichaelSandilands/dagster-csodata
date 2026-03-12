# Google Cloud Storage (GCS) Setup for CSO Data Automation

## 1. Overview

This document outlines the standard operating procedures and best practices for configuring a Google Cloud Storage (GCS) bucket to host automated CSO data extracts.

Our pipeline uses **Idempotent Loads** (replacing files) and **Change Data Capture** (only pulling when the CSO API shows updated data). To support this cleanly, we rely on **GCS Object Versioning** to handle historical archiving rather than manually managing archive folders via Python.

## 2. Bucket Naming Conventions

Bucket names in GCP must be globally unique. Use a standardized naming convention that identifies the environment, project, and purpose.

Format: `<company-prefix>-<environment>-<data-domain>-data`
Example: `myco-prod-cso-data` or `myco-dev-cso-data`

## 3. Bucket Creation & Configuration

When creating the bucket (via GCP Console or Infrastructure-as-Code like Terraform), use the following configuration:

- **Location Type**: `Region`
- **Region**: `europe-west1` (Dublin) - Since CSO is an Irish dataset, keeping the data in the Irish region ensures lowest latency and strict EU data residency.
- **Storage Class**: `Standard` (for active files).
- **Public Access Prevention**: `Enforced` (Never expose raw data buckets to the public internet).
- **Access Control**: `Uniform` (Manage access via IAM roles, not individual file ACLs).

## 4. Object Versioning & Lifecycle Rules (The Archiving Strategy)

To automatically archive older data when the `dlt` pipeline replaces a file (e.g., updating `CPM02.parquet`), we enable **Object Versioning**.

### Step 4a: Enable Object Versioning

- **Console**: Go to the bucket -> "Protection" tab -> "Object Versioning" -> Set to `Enabled`.
- **Benefit**: When the Dagster pipeline writes a new version of `CPM02.parquet`, the old version is hidden but retained. Your downstream systems always read from the same path, completely unaware of the versioning happening behind the scenes.

### Step 4b: Configure Lifecycle Management

To prevent storage costs from growing infinitely due to versioning, set up a Lifecycle Rule to transition or delete old versions.

- **Rule 1 (Cost Optimization)**: Move "Noncurrent versions" (archived files) to the `Coldline` or `Archive` storage class after **30 days**.
- **Rule 2 (Data Retention)**: Delete "Noncurrent versions" after **365 days** (or whatever your legal/business retention period dictates).

## 5. Directory Structure Best Practices

Even though GCS is an object store (not a real file system), using a logical folder hierarchy makes downstream integration with tools like BigQuery or DuckDB much easier.

We recommend the following structure for the `dlt` filesystem destination:

```Plaintext
gs://<bucket-name>/
└── raw/                  # Denotes the layer (Raw/Bronze)
    └── cso/              # Source system
        └── cube_data/    # Dataset grouping
            ├── CPM02/    # Table ID
            │   └── CPM02.parquet  (Active File)
            └── CPA01/
                └── CPA01.parquet  (Active File)
```

Configure this path in your `.env` file via `DESTINATION__FILESYSTEM__BUCKET_URL="gs://<bucket-name>/raw/cso/cube_data"`.

## 6. Service Accounts & IAM (Security)

Your automated Dagster/dlt pipeline should **never** authenticate using a personal user account.

1. **Create a Service Account (SA)**: * Name: `sa-dagster-cso-pipeline@<project-id>.iam.gserviceaccount.com`
2. **Assign the Principle of Least Privilege**:
    - Do not grant Project-level Editor roles.
    - Go to the specific GCS Bucket -> "Permissions" -> "Grant Access".
    - Add the SA and assign the `Storage Object Admin` role (allows reading, writing, and replacing files).
3. **Generate a Key**:
    - Generate a JSON key for this SA.
    - Securely store this key on your Dagster host server or inject it via secrets management.
    - Reference it in your pipeline's `.env` file as `GOOGLE_APPLICATION_CREDENTIALS`.

