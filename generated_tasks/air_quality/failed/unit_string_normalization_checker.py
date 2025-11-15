import os
import json
from pathlib import Path
from datetime import datetime, timezone

TASK_NAME = 'unit_string_normalization_checker'
TASK_DESC = "Detect malformed unit encodings (e.g., 'Âµg/m3') in metadata/CSV headers and normalize to 'µg/m3'; output a mapping to apply during parsing."
DATA_TYPE = 'air_quality'

def iso_now():
    return datetime.now(timezone.utc).isoformat()

def main():
    data_path = os.path.join('data', DATA_TYPE, 'raw_data.csv')
    out_dir = os.path.join('output', DATA_TYPE)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{TASK_NAME}_result.json")

    # Known problematic/mixed encodings mapped to normalized 'µg/m3'
    normalization_map = {
        'Âµg/m3': 'µg/m3',
        'Ã‚Âµg/m3': 'µg/m3',
        'ug/m3': 'µg/m3',
        'ug/m^3': 'µg/m3',
        'ug/m\u00b3': 'µg/m3',
        'μg/m3': 'µg/m3',
        'μg/m\u00b3': 'µg/m3',
        'µg/m\u00b3': 'µg/m3',
        'microg/m3': 'µg/m3',
        'mcg/m3': 'µg/m3'
    }

    result_summary = []

    if not Path(data_path).exists():
        msg = f"Data file not found at {data_path}"
        print(msg)
        result_summary.append({
            'name': 'error',
            'value': {'message': msg},
            'description': 'Input CSV missing; cannot scan for unit strings.',
            'timestamp': iso_now()
        })
        result = {
            'task_name': TASK_NAME,
            'description': TASK_DESC,
            'result_summary': result_summary,
            'result_generated_at': iso_now()
        }
        with open(out_path, 'w', encoding='utf-8') as f: json.dump(result, f, ensure_ascii=False, indent=2)
        return

    # Read file as text and scan for variants
    try:
        content = Path(data_path).read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
        content = Path(data_path).read_text(errors='ignore')

    found_mapping = {}
    for bad, good in normalization_map.items():
        if bad in content:
            found_mapping[bad] = good

    # Inspect header row as well
    header_line = content.splitlines()[0] if content else ''
    header_hits = {}
    for bad, good in normalization_map.items():
        if bad in header_line:
            header_hits[bad] = good

    # Prepare summary entries
    result_summary.append({
        'name': 'unit_variants_detected',
        'value': len(found_mapping),
        'description': 'Count of distinct malformed unit strings found in the CSV.',
        'timestamp': iso_now()
    })

    result_summary.append({
        'name': 'unit_mapping_suggested',
        'value': found_mapping,
        'description': "Mapping of detected malformed unit encodings to normalized 'µg/m3'. Apply during parsing/cleaning.",
        'timestamp': iso_now()
    })

    result_summary.append({
        'name': 'header_specific_hits',
        'value': header_hits,
        'description': 'Malformed unit encodings specifically found in the header row (if any).',
        'timestamp': iso_now()
    })

    # Heuristic recommendation
    recommendation = 'No malformed unit strings detected.' if not found_mapping else 'Replace detected variants with normalized \'µg/m3\' during parsing.'
    result_summary.append({
        'name': 'recommendation',
        'value': recommendation,
        'description': 'Actionable guidance based on scan results.',
        'timestamp': iso_now()
    })

    # Print concise output
    print(f"Detected {len(found_mapping)} malformed unit variants.")
    if found_mapping:
        print('Suggested normalization mapping:')
        for k, v in found_mapping.items():
            print(f"  '{k}' -> '{v}'")

    result = {
        'task_name': TASK_NAME,
        'description': TASK_DESC,
        'result_summary': result_summary,
        'result_generated_at': iso_now()
    }

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    main()