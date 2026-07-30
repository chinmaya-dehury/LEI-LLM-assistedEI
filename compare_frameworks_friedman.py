#!/usr/bin/env python3
"""
compare_frameworks_friedman.py
------------------------------
Perform the Friedman test to compare the three frameworks (LEI, AutoGen, LangGraph)
based on the number of validated codes generated.
"""

import os
import glob
import pandas as pd
import numpy as np
from scipy import stats

def main():
    print("================================================================================")
    print("              FRAMEWORK COMPARISON STATISTICAL TEST (FRIEDMAN TEST)             ")
    print("================================================================================")
    
    # 1. Discover all benchmark_results_triple.csv files
    search_pattern = os.path.join("results", "*", "benchmark_results_triple.csv")
    csv_files = glob.glob(search_pattern)
    
    # Fallback to search in all parent folders / sibling folders
    if not csv_files:
        search_pattern_sibling = os.path.join("..", "*", "results", "*", "benchmark_results_triple.csv")
        csv_files = glob.glob(search_pattern_sibling)
        
    if not csv_files:
        print("[ERROR] No 'benchmark_results_triple.csv' files found.")
        print("Please run 'python benchmark_runner_triple.py' first to collect benchmarking results.")
        return 1
        
    print(f"Found {len(csv_files)} benchmark results files:")
    for f in csv_files:
        print(f"  - {f}")
        
    # 2. Load and aggregate the data
    all_data = []
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            # Normalize column names
            df.columns = [c.strip().lower() for c in df.columns]
            all_data.append(df)
        except Exception as e:
            print(f"[WARNING] Could not read {csv_file}: {e}")
            
    if not all_data:
        print("[ERROR] No valid data could be loaded.")
        return 1
        
    df_all = pd.concat(all_data, ignore_index=True)
    
    # Check required columns
    required_cols = {'dataset', 'framework', 'code_passed'}
    if not required_cols.issubset(df_all.columns):
        # check if 'validator_passed' exists
        if 'validator_passed' in df_all.columns:
            df_all['code_passed'] = df_all['validator_passed']
        else:
            print(f"[ERROR] Missing required columns. Found columns: {list(df_all.columns)}")
            return 1
            
    # Clean framework names
    df_all['framework'] = df_all['framework'].str.strip()
    
    # Filter for the three main frameworks
    target_frameworks = ["LEI", "AutoGen", "LangGraph"]
    df_filtered = df_all[df_all['framework'].isin(target_frameworks)].copy()
    
    if df_filtered.empty:
        print(f"[ERROR] No data found for target frameworks: {target_frameworks}")
        return 1
        
    # We need to construct blocks of (dataset, run_number / synthetic index) where all three frameworks have data.
    df_filtered['run_idx'] = df_filtered.groupby(['dataset', 'framework']).cumcount() + 1
    
    # Pivot to get frameworks as columns
    pivot_df = df_filtered.pivot_table(
        index=['dataset', 'run_idx'],
        columns='framework',
        values='code_passed',
        aggfunc='first'
    )
    
    # Drop rows that don't have all three frameworks
    pivot_clean = pivot_df.dropna(subset=target_frameworks)
    
    if pivot_clean.empty:
        print("[ERROR] No paired runs found where all three frameworks (LEI, AutoGen, LangGraph) have results.")
        print("Data available in pivot table:")
        print(pivot_df)
        return 1
        
    print(f"\nAggregated {len(pivot_clean)} paired blocks (runs) across datasets:")
    print(pivot_clean)
    
    # 3. Perform the Friedman Test
    lei_scores = pivot_clean['LEI'].values
    autogen_scores = pivot_clean['AutoGen'].values
    langgraph_scores = pivot_clean['LangGraph'].values
    
    try:
        stat, p_value = stats.friedmanchisquare(lei_scores, autogen_scores, langgraph_scores)
        
        # Calculate mean ranks (Rank 1 is best: highest score gets rank 1)
        ranks = pivot_clean[target_frameworks].rank(axis=1, ascending=False)
        mean_ranks = ranks.mean()
        
        print("\n" + "="*50)
        print("                 FRIEDMAN TEST RESULTS                  ")
        print("="*50)
        print(f"Friedman Q Statistic: {stat:.4f}")
        print(f"p-value:              {p_value:.6f}")
        print("-"*50)
        print("Mean Ranks (Lower is better / higher success rate):")
        for fw in target_frameworks:
            print(f"  {fw:<12}: {mean_ranks[fw]:.3f}")
        print("="*50)
        
        # Interpretation
        alpha = 0.05
        if p_value < alpha:
            print(f"\n[SIGNIFICANT] The difference between the frameworks is statistically significant (p < {alpha}).")
            print("Null hypothesis rejected: The frameworks do not perform equally.")
        else:
            print(f"\n[NOT SIGNIFICANT] The difference between the frameworks is NOT statistically significant (p >= {alpha}).")
            print("Failed to reject null hypothesis: The frameworks perform equally.")
            
    except Exception as e:
        print(f"[ERROR] Friedman test execution failed: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    main()
