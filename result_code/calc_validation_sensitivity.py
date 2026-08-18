import json
import os
import pandas as pd

def calculate_rsys(p0, p1, p2, f, beta1, beta2):
    numerator = p0 + (beta1 * p1) + (beta2 * p2)
    denominator = p0 + p1 + p2 + f
    if denominator == 0:
        return 0.0
    return numerator / denominator

def main():
    base_dir = r"C:\Users\DELL\Downloads\result-all-cloud-lei\validator"
    out_csv = r"C:\Users\DELL\Downloads\result-all-cloud-lei\validator\validation_success_details.csv"
    
    # Beta configurations as requested
    beta_configs = {
        "baseline": (0.90, 0.80),
        "harsh": (0.70, 0.50),
        "lenient": (0.95, 0.90),
        "equal": (1.00, 1.00),
        "steep_decay": (0.80, 0.40),
        "moderate": (0.85, 0.70)
    }

    results = []

    for ds in sorted(os.listdir(base_dir)):
        ds_path = os.path.join(base_dir, ds)
        if not os.path.isdir(ds_path):
            continue
            
        for f in sorted(os.listdir(ds_path)):
            if "all_runs.json" not in f:
                continue
                
            fp = os.path.join(ds_path, f)
            with open(fp, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                
            model = data.get("model", "unknown")
            tasks = []
            if "tasks" in data:
                tasks = data["tasks"]
            elif "runs" in data:
                for run_id, run_tasks in data["runs"].items():
                    tasks.extend(run_tasks)
            
            p0 = 0
            p1 = 0
            p2 = 0
            fail = 0
            ignored = 0
            
            for t in tasks:
                msg = t.get("message", "").strip()
                if msg == "Executed and validated successfully":
                    p0 += 1
                elif msg == "Fixed after 1 attempt(s)":
                    p1 += 1
                elif msg == "Fixed after 2 attempt(s)":
                    p2 += 1
                elif msg == "Failed after 2 correction attempts":
                    fail += 1
                elif "script file not found" in msg.lower() or "script not found" in msg.lower():
                    ignored += 1
                else:
                    # In case of variations, we map them carefully based on code_passed and validator_passed
                    # but mostly rely on the exact strings the user provided
                    if t.get("validator_passed"):
                        # If passed but unrecognized message, assume P0 for safety if we must, 
                        # but ideally user strings are exact. Let's strictly follow user strings.
                        pass
            
            row = {
                "dataset": ds,
                "model": model,
                "P0": p0,
                "P1": p1,
                "P2": p2,
                "F": fail,
                "Ignored": ignored,
                "Total_Valid_Tasks": p0 + p1 + p2 + fail
            }
            
            # Calculate R_sys for each beta configuration
            for label, (b1, b2) in beta_configs.items():
                rsys = calculate_rsys(p0, p1, p2, fail, b1, b2)
                row[f"R_sys_{label}"] = round(rsys, 4)
                
            results.append(row)

    df = pd.DataFrame(results)
    
    # Reorder columns slightly for better readability
    cols = ["model", "dataset", "Total_Valid_Tasks", "P0", "P1", "P2", "F", "Ignored"]
    beta_cols = [c for c in df.columns if c.startswith("R_sys_")]
    df = df[cols + beta_cols]
    
    # Sort for consistent output
    df = df.sort_values(by=["model", "dataset"])
    
    df.to_csv(out_csv, index=False)
    print(f"Generated validation sensitivity details: {out_csv}")
    
    print("\nSummary preview:")
    print(df.head())

if __name__ == "__main__":
    main()
