# Metadata Template Documentation (`metadata_template.json`)

This document explains the structure and meaning of each field defined in `metadata_template.json`. This metadata is supplied to the LLM to give it semantic understanding of the data schema, quality expectations, and hardware constraints of the target edge device.

---

## Field Reference

### 1. `domain`
* **Type**: `string`
* **Meaning**: The general application area or dataset category.
* **Examples**: `"air_quality"`, `"agri-data"`, `"meteo-data"`, `"lab-data"`

---

### 2. `data_source`
Describes the source, collection, and format of the raw dataset.

* **`source_type`**: `string` (restricted to `"sensor"`, `"api"`, or `"database"`)
  * **Meaning**: The source from which the dataset is generated:
    * `"sensor"`: Direct physical sensor readings (e.g. IoT agricultural node).
    * `"api"`: Pulled from an external web API/service (e.g. weather forecast).
    * `"database"`: Extracted from local database/file storage.
* **`provider`**: `string`
  * **Meaning**: The name of the organization, platform, or hardware node supplying the data.
  * **Example**: `"Precision Smart Agriculture IoT Sensing Campaign"`
* **`sampling_interval`**: `string`
  * **Meaning**: The frequency at which the data is recorded.
  * **Examples**: `"daily"`, `"hourly"`, `"10_minutes"`, `"real-time"`
* **`data_format`**: `string` (restricted to `"csv"`, `"json"`, or `"parquet"`)
  * **Meaning**: The serialization format of the raw data.
  * **Example**: `"csv"`

---

### 3. `columns`
An array of objects describing each column present in the dataset.

* **`name`**: `string`
  * **Meaning**: The exact name of the column header (case-sensitive).
  * **Example**: `"Temperature"`
* **`type`**: `string` (restricted to `"float"`, `"integer"`, `"string"`, or `"datetime"`)
  * **Meaning**: The data type representation in python.
  * **Example**: `"float"`
* **`unit`**: `string` or `null`
  * **Meaning**: The unit of measurement. Use `null` if the column is unitless, or `"categorical"` if it is an encoded label.
  * **Examples**: `"C"`, `"ppm"`, `null`, `"categorical"`
* **`range`**: `object` or `null`
  * **Meaning**: The valid bounds of the data values.
  * **Fields**:
    * `min`: Minimum possible value.
    * `max`: Maximum possible value.
* **`description`**: `string`
  * **Meaning**: A human-readable semantic explanation of what this column represents.
  * **Example**: `"Percentage of water content in the soil"`

---

### 4. `data_quality`
Assesses the reliability of the dataset.

* **`missing_values`**: `string` (restricted to `"none"` or `"allowed"`)
  * **Meaning**: Whether null or missing values are permitted in the dataset.
* **`sensor_accuracy`**: `string`
  * **Meaning**: The accuracy/calibration of the recording hardware (e.g. `"high"`, `"low"`).

---

### 5. `device_specs`
Details the hardware capabilities of the target edge deployment node.

* **`edge_device`**: `string`
  * **Meaning**: Name/model of the deployment hardware.
  * **Example**: `"Smart Farming Sensor Node"`
* **`cpu`**: `string`
  * **Meaning**: The processor model.
  * **Example**: `"ARM Cortex-M7"`
* **`memory`**: `string`
  * **Meaning**: The RAM size and type.
  * **Example**: `"512KB SRAM"`

---

### 6. `resource_constraints`
Defines operational boundaries for generated code scripts.

* **`max_cpu_percent`**: `integer`
  * **Meaning**: The maximum allowed CPU usage threshold for generated scripts.
  * **Example**: `80`
* **`max_memory_percent`**: `integer`
  * **Meaning**: The maximum allowed memory allocation threshold.
  * **Example**: `80`
* **`lightweight_execution_required`**: `boolean`
  * **Meaning**: Tells the LLM to avoid heavy libraries (like TensorFlow/PyTorch) and write simple, optimized code.

---

### 7. `storage`
Details how the data is stored locally and synchronized with the cloud.

* **`type`**: `string` (restricted to `"csv"`, `"sqlite"`, or `"timeseries_db"`)
  * **Meaning**: The local storage layout.
* **`sync_policy`**: `string` (restricted to `"local"` or `"periodic_cloud_sync"`)
  * **Meaning**: How data updates are synced.
    * `"local"`: Stored only on-device.
    * `"periodic_cloud_sync"`: Synced to a remote repository periodically.
