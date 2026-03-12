from pathlib import Path

from dagster import (
    definitions, 
    load_from_defs_folder,
    Definitions,
    define_asset_job,
    AssetSelection,
    ScheduleDefinition
)

# 1. Define the Job
# AssetSelection.all() targets all the assets currently in your project.
cso_data_job = define_asset_job(
    name="cso_data_extraction_job",
    selection=AssetSelection.all()
)

# 2. Define the Schedule
# This cron string "0 2 * * *" means it will run every day at 2:00 AM.
cso_daily_schedule = ScheduleDefinition(
    name="cso_daily_schedule",
    job=cso_data_job,
    cron_schedule="0 2 * * *",
    execution_timezone="Europe/Dublin"
)

# 3. Merge the components with your new schedule
@definitions
def defs():
    # Load your DLT components
    component_defs = load_from_defs_folder(path_within_project=Path(__file__).parent)
    
    # Merge them with standard definitions (Jobs and Schedules)
    return Definitions.merge(
        component_defs,
        Definitions(
            jobs=[cso_data_job],
            schedules=[cso_daily_schedule]
        )
    )
