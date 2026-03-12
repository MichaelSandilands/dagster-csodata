import dlt
import requests
from pyjstat import pyjstat
from typing import List

@dlt.source(name="cso_api")
def cso_data_source(table_ids: List[str]):
    """
    Generalizable source for CSO Cube Data.
    Yields a resource for each table ID provided (e.g., "CPM02").
    """
    for table_id in table_ids:
        # Rename the resource dynamically so dlt creates separate folders/tables
        yield cso_cube_resource(table_id).with_name(table_id)


@dlt.resource(write_disposition="replace")
def cso_cube_resource(table_id: str):
    """
    Fetches, parses, and yields CSO JSON-stat data for a given table_id.
    Tracks the 'updated' timestamp to only update GCS when new data is available.
    """
    url = f"https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/{table_id}/JSON-stat/2.0/en"
    
    # 1. Fetch the raw JSON
    response = requests.get(url)
    response.raise_for_status()
    raw_json = response.json()
    
    # 2. Extract the 'updated' metadata from the JSON-stat payload
    updated_at = raw_json.get("updated")
    
    # 3. Use dlt state to check if we already have this exact version
    state = dlt.current.resource_state()
    last_updated = state.get("last_updated")
    
    if updated_at and last_updated == updated_at:
        # The data hasn't changed since the last run. 
        # By yielding nothing, dlt gracefully skips writing to GCS.
        return
        
    # 4. If updated, parse with pyjstat and convert to Pandas DataFrame
    dataset = pyjstat.Dataset.read(response.text)
    df = dataset.write('dataframe')
    
    # 5. Update the state with the new timestamp and yield the data
    state["last_updated"] = updated_at
    yield df

# Define the pipeline.
# Note: We do NOT hardcode credentials or bucket URLs here. That belongs in .env.
cso_pipeline = dlt.pipeline(
    pipeline_name="cso_to_gcs",
    destination="filesystem",
    dataset_name="cso_cube_data"
)

# Example instantiation for Dagster assets to pick up
cso_load_source = cso_data_source(table_ids=["CPM02", "CPA01"])
