# Project Summary: Scheduling Algorithm Fairness Analysis

## Objective
This project aims to systematically evaluate and compare the fairness and performance of three fundamental CPU scheduling algorithms: **First-Come, First-Served (FCFS)**, **Priority Scheduling**, and **Round Robin (RR)**. The core focus is on quantifying "Fairness" and "Starvation" using real-world historical data logs rather than synthetic approximations.

## Accomplishments
1.  **Dataset Acquisition:** Harvested **10 authentic real-world HPC traces** in Standard Workload Format (SWF) from the Parallel Workloads Archive:
    - `SDSC-SP2`
    - `SDSC-BLUE`
    - `ANL-Intrepid`
    - `CTC-SP2`
    - `HPC2N`
    - `KTH-SP2`
    - `CEA-Curie`
    - `PIK-IPLEX`
    - `RICC`
    - `Lublin-1024`
2.  **Algorithm Implementation:** Built a robust discrete-event simulation engine in Python (`run_scheduling_analysis.py`) to process these workloads and calculate:
    - **Performance Metrics:** AWT, ATAT, Response Time, Throughput, CPU Utilization.
    - **Fairness Metrics:** Jain's Fairness Index (JFI), Gini Coefficient for Waiting Time, Starvation Count.
3.  **Visualization:** Generated comparative bar charts for all 10 datasets across key fairness indicators (saved in the `images/` directory).
4.  **Interactive Research:** Developed `Final_Scheduling_Analysis.ipynb`, a Jupyter Notebook that allows for live, interactive re-evaluation and visualization of the data.
5.  **Scientific Manuscript:** Authored `Review_Paper.md`, a comprehensive review paper documenting the methodology, empirical results, and technical conclusions of the survey.

## Repository Contents
- **SWF Files:** The raw trace data used for the simulation.
- **Python Scripts:** The analysis engine and automation tools.
- **Jupyter Notebook:** Interactive environment for showing work.
- **Images:** Visual evidence of algorithm performance.
- **Review Paper:** Final academic synthesis of the research.

## Conclusion
The analysis demonstrates that Round Robin consistently outperforms FCFS in managing real-world, bursty HPC workloads by mitigating the "Convoy Effect" and minimizing Response Time, despite the inherent context-switching overhead. Priority scheduling, while hierarchically efficient, demonstrates a persistent risk of starvation across all 10 real-world scenarios.
