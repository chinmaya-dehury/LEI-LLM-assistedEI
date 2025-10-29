
# Paths = Data type specific
# MAke sure that a fodler name with following data type exists inside 
#   data/, generated_tasks/ and output/ folders.
#
#### Select any one data type by uncommenting the line below

# DATA_TYPE = "temp_humidity" # it is expected that a folder with this name exists
DATA_TYPE = "air_quality" # it is expected that a folder with this name exists

###### Task code generator configuration  ######
NO_OF_TASKS = 2  # Number of tasks to generate code for at a time


#### scheduler/edge executor configuration ######
parallel_execution = False  # If True, execute tasks in parallel; else sequentially
parallel_execution_limit = 2  # Max number of parallel tasks if parallel_execution is True, DEFAULT value is 1
# Note: Make sure the edge device can handle this many parallel tasks without overload.