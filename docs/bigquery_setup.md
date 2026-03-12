# BigQuery Initialization & Architecture Guide

## 1. Overview

This document outlines the setup and configuration of Google BigQuery for the CSO Data Platform.

Our architecture follows the `Data Lakehouse` pattern. Instead of copying raw data from Google Cloud Storage (GCS) into BigQuery storage (which doubles storage costs and pipeline complexity), we will configure BigQuery to read the `.parquet` files directly from GCS using `External Tables`. BigQuery will serve exclusively as our compute engine and the storage layer for our cleaned, downstream dbt models (Silver/Gold layers).

## 2. Prerequisites

- A Google Cloud Project (e.g., `cso-elt-pipeline`).
- The GCS Bucket successfully configured and populated with raw `.parquet` files by our `dlt` pipeline.
- A Service Account already created.

# 3. Initialize BigQuery

### 3.1 Enable the BigQuery API

Before using BigQuery, ensure the API is enabled in your Google Cloud Project.

- Navigate to the Google Cloud Console.
- In the search bar, type **BigQuery API** and select it.
- If it is not already enabled, click **Enable**.

### 3.2: Create the BigQuery Datasets (Namespaces)

In BigQuery, a "Dataset" is equivalent to a schema or namespace in a traditional database. We need to create distinct datasets to separate our raw external tables from our transformed `dbt` models.

#### Naming Convention & Layers

We will follow a standard medallion architecture:

- `raw_cso` (Bronze): This dataset will hold the External Tables pointing to GCS. No actual data is stored here.
- `staging_cso` (Silver): This dataset will hold `dbt` views/tables that clean, cast, and rename the raw data.
- `marts_cso` (Gold): This dataset will hold the final, business-ready aggregations and joined tables.

#### How to Create the Datasets

1. Open the BigQuery UI in the Google Cloud Console.
2. In the Explorer pane, click the three dots next to your Project ID and select Create dataset.
3. Dataset ID: Enter raw_cso.
4. Location type: Select Region and choose europe-west1 (Belgium/Dublin) — CRITICAL: This must perfectly match the region where your GCS bucket is located, otherwise BigQuery cannot read the files.
5. Click Create dataset.
6. Repeat this process for staging_cso and marts_cso.

### 3.3: Configure IAM Permissions (Service Account)

Your Dagster/dbt pipeline needs permission to execute SQL queries in BigQuery and read the files from GCS.

We will update the existing Service Account (used for google cloud storage dlt) with the following roles:

1. Copy the full email address of your Service Account from the Service Accounts page.
2. Go back to **IAM & Admin** > **IAM**.
3. Near the top of the page, click the **+ GRANT ACCESS** button.
4. In the **New principals** box, paste the Service Account email address.
5. Add the following roles:
   * **`BigQuery User`**: Allows dbt to run queries, read metadata, and list datasets.
   * **`BigQuery Data Editor`**: Allows dbt to create, update, and drop tables/views inside your datasets.
   * **`BigQuery Read Session User`**: *(Optional but recommended)* Required if you plan to use the new dbt Fusion engine or BigQuery Storage Read API.
   * *(Note: Ensure the account still has `Storage Object Admin` or `Storage Object Viewer` from the GCS setup phase so BigQuery can read the external parquet files).*
6. Click **Save**.

### 3.4 Connecting dbt to BigQuery (External Tables)

Because we are using External Tables, we do not write Python code to ingest data into BigQuery. Instead, we configure `dbt` to mount the GCS files as tables.

When setting up your `dbt` project, you will install the `dbt-external-tables` package.

#### Example sources.yml Configuration

Here is how you will define the CSO data so `dbt` can create the external tables in the `raw_cso` dataset automatically:

```YAML
version: 2

sources:
  - name: cso_cube_data
    database: myco-data-platform-dev  # Your GCP Project ID
    schema: raw_cso                   # The BigQuery Dataset for raw data
    tables:
      - name: cpm02
        description: "Raw CSO dataset CPM02"
        external:
          location: "gs://<bucket-name>/raw/cso/cso_cube_data/cpm02/*.parquet"
          source_format: PARQUET
      - name: cpa01
        description: "Raw CSO dataset CPA01"
        external:
          location: "gs://<bucket-name>/raw/cso/cso_cube_data/cpa01/*.parquet"
          source_format: PARQUET
```

When you run `dbt run-operation stage_external_sources`, dbt will execute the exact DDL (Data Definition Language) in BigQuery to mount these GCS paths as queryable tables!
