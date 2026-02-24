import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)

def load_swf(filename, max_rows=200):
    data = []
    if not os.path.exists(filename):
        print(f"Warning: {filename} not found.")
        return pd.DataFrame()
        
    with open(filename, 'r') as f:
        count = 0
        for line in f:
            line = line.strip()
            if not line or line.startswith(';'): continue
            parts = line.split()
            if len(parts) < 18: continue
            try:
                pid = int(parts[0])
                submit = float(parts[1])
                run = float(parts[3])
                req_procs = int(parts[7])
                if run <= 0: run = 1 # give it at least 1ms to avoid DIV/0
                prio = min(10, max(1, req_procs)) # proxy priority based on requested processors
                data.append({'pid': pid, 'arrivalTime': submit, 'priority': prio, 'processTime': int(run)})
                count += 1
                if count >= max_rows: break
            except ValueError:
                continue
    df = pd.DataFrame(data)
    if not df.empty:
        df.sort_values(by='arrivalTime', inplace=True)
        df['arrivalTime'] = df['arrivalTime'] - df['arrivalTime'].min()
    return df

def generate_datasets():
    datasets = {}
    n_processes = 200

    # 10 Real World Traces:
    datasets['Real SDSC SP2'] = load_swf('SDSC-SP2.swf', n_processes)
    datasets['Real SDSC BLUE'] = load_swf('SDSC-BLUE.swf', n_processes)
    datasets['Real ANL Intrepid'] = load_swf('ANL-Intrepid.swf', n_processes)
    datasets['Real CTC SP2'] = load_swf('CTC-SP2.swf', n_processes)
    datasets['Real HPC2N'] = load_swf('HPC2N.swf', n_processes)
    datasets['Real KTH SP2'] = load_swf('KTH-SP2.swf', n_processes)
    datasets['Real CEA Curie'] = load_swf('CEA-Curie.swf', n_processes)
    datasets['Real PIK IPLEX'] = load_swf('PIK-IPLEX.swf', n_processes)
    datasets['Real RICC'] = load_swf('RICC.swf', n_processes)
    datasets['Real Lublin'] = load_swf('Lublin-1024.swf', n_processes)

    # Note: excluding the synthetic ones entirely this time per user request. 
    return {k: v for k, v in datasets.items() if not v.empty}

def calculate_extended_metrics(df, total_time, quantum=None):
    df["TurnaroundTime"] = df["FinishTime"] - df["arrivalTime"]
    df["WaitingTime"] = df["TurnaroundTime"] - df["processTime"]
    df["ResponseTime"] = df["StartTime"] - df["arrivalTime"]
    
    metrics = {}
    metrics['AWT'] = df["WaitingTime"].mean()
    metrics['ATAT'] = df["TurnaroundTime"].mean()
    metrics['Response Time'] = df["ResponseTime"].mean()
    metrics['MWT'] = df["WaitingTime"].max()
    metrics['Throughput'] = len(df) / total_time if total_time > 0 else 0
    
    total_burst = df["processTime"].sum()
    metrics['CPU Utilization (%)'] = (total_burst / total_time) * 100 if total_time > 0 else 0
    
    # 2. Resource waste/idle time
    first_arrival = df["arrivalTime"].min()
    idle_time = total_time - total_burst - first_arrival
    metrics['Idle Time'] = idle_time if idle_time > 0 else 0
    
    sum_wt = df["WaitingTime"].sum()
    sum_sq_wt = (df["WaitingTime"]**2).sum()
    n = len(df)
    metrics['JFI'] = (sum_wt**2) / (n * sum_sq_wt) if sum_sq_wt > 0 else 1.0
    
    def gini(array):
        array = np.sort(array)
        index = np.arange(1, array.shape[0] + 1)
        nn = array.shape[0]
        return (np.sum((2 * index - nn  - 1) * array)) / (nn * np.sum(array)) if np.sum(array) > 0 else 0
    metrics['Gini (WT)'] = gini(df["WaitingTime"].values)
    
    avg_burst = df["processTime"].mean()
    starvation_threshold = 3 * avg_burst
    metrics['Starvation Count'] = len(df[df["WaitingTime"] > starvation_threshold])
    
    # 1. Preemption frequency
    # 8. Dynamic task switching efficiency
    cs_count = len(df)
    if 'Preemptions' in df.columns:
        cs_count += df['Preemptions'].sum()
    metrics['Preemption Frequency'] = cs_count / n if n > 0 else 0
    
    # Assuming 0.1 time unit per context switch
    cs_overhead = 0.1 * cs_count
    metrics['Task Switching Eff (%)'] = (total_burst / (total_burst + cs_overhead)) * 100 if (total_burst + cs_overhead) > 0 else 0

    # 3. Priority inversion potential
    # If a high priority job arrived and is waiting while a lower priority job is executing
    inversion_count = 0
    # 5. Fairness bias / fairness to low-priority jobs
    # Correlation between priority and waiting time.
    # Higher priority (lower number in typical OS, but here we used min(10, req_procs), let's keep it straight metric-wise)
    # The higher the value of 'priority' column here, the higher the "priority".
    # A negative correlation means higher priority gets lower waiting time (fairness to priority, bias against low).
    
    if n > 0:
        for idx, row in df.iterrows():
            arr, prio = row['arrivalTime'], row['priority']
            # Find jobs with lower priority that were executing when this higher priority job arrived
            # This is simpler logic just evaluating temporal overlap
            if prio > 1:
                lower_prio_executing = df[(df['priority'] < prio) & (df['StartTime'] < arr) & (df['FinishTime'] > arr)]
                if not lower_prio_executing.empty:
                    inversion_count += len(lower_prio_executing)
                    
        metrics['Priority Inversion Potential'] = inversion_count
        
        # Pearson correlation
        std_prio = df['priority'].std()
        std_wt = df['WaitingTime'].std()
        if std_prio > 0 and std_wt > 0:
            metrics['Fairness Bias (Corr)'] = df['priority'].corr(df['WaitingTime'])
        else:
            metrics['Fairness Bias (Corr)'] = 0.0
            
    # 6. Fairness over time
    # Split the dataset into first half and second half temporally
    if n > 1:
        mid_time = first_arrival + (total_time - first_arrival) / 2
        df_first = df[df['arrivalTime'] <= mid_time]
        df_second = df[df['arrivalTime'] > mid_time]
        
        def safe_jfi(sub_df):
            if sub_df.empty: return 1.0
            s_wt = sub_df["WaitingTime"].sum()
            ss_wt = (sub_df["WaitingTime"]**2).sum()
            return (s_wt**2) / (len(sub_df) * ss_wt) if ss_wt > 0 else 1.0
            
        metrics['JFI First Half'] = safe_jfi(df_first)
        metrics['JFI Second Half'] = safe_jfi(df_second)
    else:
        metrics['JFI First Half'] = 1.0
        metrics['JFI Second Half'] = 1.0

    # 7. Throughput vs. fairness metric 
    # Ratio of Throughput to Gini Inequality index - higher is better performance-fairness balance
    gt = metrics['Gini (WT)']
    metrics['Throughput to Gini'] = metrics['Throughput'] / gt if gt > 0 else metrics['Throughput']

    return metrics

def fcfs_schedule(df_in):
    df = df_in.copy().sort_values(by='arrivalTime').reset_index(drop=True)
    current_time = 0
    start_times, finish_times = [], []
    for arr, burst in zip(df['arrivalTime'], df['processTime']):
        start = max(current_time, arr)
        start_times.append(start)
        finish = start + burst
        finish_times.append(finish)
        current_time = finish
    df['StartTime'] = start_times
    df['FinishTime'] = finish_times
    df['Preemptions'] = 0
    return df, current_time

def priority_schedule(df_in): 
    # Non-preemptive, higher number = higher priority
    df = df_in.copy().sort_values(by=['arrivalTime', 'priority'], ascending=[True, False]).reset_index(drop=True)
    ready_queue = []
    current_time = 0
    completed = 0
    n = len(df)
    
    start_times = np.zeros(n)
    finish_times = np.zeros(n)
    is_completed = np.zeros(n, dtype=bool)
    
    while completed < n:
        arrived = df[(df['arrivalTime'] <= current_time) & (~is_completed)]
        if arrived.empty:
            next_arrival = df.loc[~is_completed, 'arrivalTime'].min()
            current_time = next_arrival
            arrived = df[(df['arrivalTime'] <= current_time) & (~is_completed)]
            
        # Pick highest priority
        idx = arrived['priority'].idxmax()
        start = current_time
        burst = df.loc[idx, 'processTime']
        finish = start + burst
        
        start_times[idx] = start
        finish_times[idx] = finish
        is_completed[idx] = True
        
        current_time = finish
        completed += 1
        
    df['StartTime'] = start_times
    df['FinishTime'] = finish_times
    df['Preemptions'] = 0
    return df, current_time

def round_robin_schedule(df_in, quantum):
    df = df_in.copy().sort_values(by='arrivalTime').reset_index(drop=True)
    n = len(df)
    remaining_burst = df['processTime'].values.copy()
    start_times = np.full(n, -1.0)
    finish_times = np.zeros(n)
    preemptions = np.zeros(n)
    
    current_time = 0
    completed = 0
    queue = []
    
    idx_arrived = 0
    
    while completed < n:
        while idx_arrived < n and df.loc[idx_arrived, 'arrivalTime'] <= current_time:
            queue.append(idx_arrived)
            idx_arrived += 1
            
        if not queue:
            current_time = df.loc[idx_arrived, 'arrivalTime']
            continue
            
        curr_proc = queue.pop(0)
        if start_times[curr_proc] == -1:
            start_times[curr_proc] = current_time
            
        time_to_run = min(quantum, remaining_burst[curr_proc])
        current_time += time_to_run
        remaining_burst[curr_proc] -= time_to_run
        
        while idx_arrived < n and df.loc[idx_arrived, 'arrivalTime'] <= current_time:
            queue.append(idx_arrived)
            idx_arrived += 1
            
        if remaining_burst[curr_proc] == 0:
            finish_times[curr_proc] = current_time
            completed += 1
        else:
            queue.append(curr_proc)
            preemptions[curr_proc] += 1
            
    df['StartTime'] = start_times
    df['FinishTime'] = finish_times
    df['Preemptions'] = preemptions
    return df, current_time

def run_analysis():
    datasets = generate_datasets()
    all_results = []
    
    # To store data for 9. Job-wait distribution
    all_job_waits = []
    
    for ds_name, ds_df in datasets.items():
        mean_burst = ds_df['processTime'].mean()
        quantum = int(mean_burst / 2) if int(mean_burst / 2) > 0 else 1
        
        # FCFS
        res_fcfs, tt_fcfs = fcfs_schedule(ds_df)
        m_fcfs = calculate_extended_metrics(res_fcfs, tt_fcfs)
        m_fcfs['Algorithm'] = 'FCFS'
        m_fcfs['Dataset'] = ds_name
        
        # Priority
        res_prio, tt_prio = priority_schedule(ds_df)
        m_prio = calculate_extended_metrics(res_prio, tt_prio)
        m_prio['Algorithm'] = 'Priority'
        m_prio['Dataset'] = ds_name
        
        # Round Robin
        res_rr, tt_rr = round_robin_schedule(ds_df, quantum)
        m_rr = calculate_extended_metrics(res_rr, tt_rr, quantum)
        m_rr['Algorithm'] = 'Round Robin'
        m_rr['Dataset'] = ds_name
        
        all_results.extend([m_fcfs, m_prio, m_rr])
        
        # Save raw waiting times for the Job-wait distribution plot
        for _, row in res_fcfs.iterrows():
            all_job_waits.append({'Dataset': ds_name, 'Algorithm': 'FCFS', 'WaitingTime': row['WaitingTime']})
        for _, row in res_prio.iterrows():
            all_job_waits.append({'Dataset': ds_name, 'Algorithm': 'Priority', 'WaitingTime': row['WaitingTime']})
        for _, row in res_rr.iterrows():
             all_job_waits.append({'Dataset': ds_name, 'Algorithm': 'Round Robin', 'WaitingTime': row['WaitingTime']})
        
    results_df = pd.DataFrame(all_results)
    
    # Generate Plots
    metrics_to_plot = [
        'AWT', 'Response Time', 'JFI', 'Starvation Count', 
        'MWT', 'Preemption Frequency', 'Idle Time', 'Priority Inversion Potential',
        'Fairness Bias (Corr)', 'Throughput to Gini', 'Task Switching Eff (%)'
    ]
    
    if not os.path.exists("images"):
        os.makedirs("images")
        
    for metric in metrics_to_plot:
        plt.figure(figsize=(14, 8))
        sns.barplot(data=results_df, x='Dataset', y=metric, hue='Algorithm')
        plt.title(f'{metric} Comparison across Datasets')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(f'images/{metric.replace(" ", "_").replace("%", "Pct").replace("(", "").replace(")", "")}.png')
        plt.close()
        
    # Plot 6. Fairness over time (JFI First vs Second Half)
    time_df = pd.melt(results_df, id_vars=['Dataset', 'Algorithm'], value_vars=['JFI First Half', 'JFI Second Half'], 
                      var_name='Time_Period', value_name='JFI_Value')
    plt.figure(figsize=(14, 8))
    sns.catplot(data=time_df, x='Dataset', y='JFI_Value', hue='Algorithm', col='Time_Period', kind='bar', height=6, aspect=1.2)
    plt.tight_layout()
    plt.savefig('images/Fairness_Over_Time.png')
    plt.close('all')
        
    # Plot 9. Job-wait distribution
    waits_df = pd.DataFrame(all_job_waits)
    plt.figure(figsize=(14, 8))
    # Using log scale to better visualize distributions since AWT can be insanely high in HPC
    waits_df['LogWaitingTime'] = np.log1p(waits_df['WaitingTime'])
    sns.violinplot(data=waits_df, x='Dataset', y='LogWaitingTime', hue='Algorithm', split=False, cut=0)
    plt.title('Job-Wait Distribution (Log Scale) across Datasets')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig('images/Job_Wait_Distribution.png')
    plt.close()
        
    results_df.to_csv("results.csv", index=False)
    print(f"Analysis finished successfully on {len(datasets)} explicit real-world datasets. Saved images and CSV.")

if __name__ == "__main__":
    run_analysis()
