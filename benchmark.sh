#!/bin/bash

# Benchmark script for comparing photogrammetry methods
# This script runs all available methods on test datasets and generates performance reports

set -e

DATASET_PATH="/app/360_scenes"
RESULTS_PATH="/app/results/benchmarks"
METHODS=("meshroom" "colmap" "openmvg" "instant-ngp" "gaussian-splatting" "mobilenerf" "pifuhd")
DATASETS=("bicycle" "bonsai" "counter" "flowers" "garden" "kitchen" "treehill")

echo "🔬 Starting Photogrammetry Pipeline Benchmarks"
echo "=============================================="

# Create benchmark results directory
mkdir -p "$RESULTS_PATH"

# Function to run benchmark for a method and dataset
run_benchmark() {
    local method=$1
    local dataset=$2
    local start_time=$(date +%s)
    
    echo "📊 Testing $method on $dataset dataset..."
    
    # Create job ID
    local job_id="benchmark_${method}_${dataset}_$(date +%s)"
    
    # Start reconstruction
    curl -X POST "http://core:5000/reconstruct" \
        -F "job_id=$job_id" \
        -F "method=$method" \
        -F "dataset_name=$dataset" \
        -F "parameters={\"benchmark_mode\": true}"
    
    # Poll for completion
    local status="queued"
    while [ "$status" != "completed" ] && [ "$status" != "failed" ]; do
        sleep 30
        local response=$(curl -s "http://core:5000/status/$job_id")
        status=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")
        echo "   Status: $status"
    done
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Record results
    local result_file="$RESULTS_PATH/${method}_${dataset}_results.json"
    cat > "$result_file" << EOF
{
    "method": "$method",
    "dataset": "$dataset",
    "job_id": "$job_id",
    "status": "$status",
    "duration_seconds": $duration,
    "start_time": $start_time,
    "end_time": $end_time
}
EOF
    
    echo "   ✅ Completed in ${duration}s"
    return 0
}

# Function to check if a method container is available
check_method_available() {
    local method=$1
    if docker compose ps | grep -q "${method}.*Up"; then
        return 0
    else
        return 1
    fi
}

# Main benchmark loop
for dataset in "${DATASETS[@]}"; do
    echo ""
    echo "🗂️  Processing dataset: $dataset"
    echo "================================"
    
    for method in "${METHODS[@]}"; do
        if check_method_available "$method"; then
            run_benchmark "$method" "$dataset"
        else
            echo "   ⚠️  Skipping $method (container not available)"
        fi
    done
done

# Generate summary report
echo ""
echo "📈 Generating benchmark summary..."

python3 << 'EOF'
import json
import os
from pathlib import Path

results_dir = Path(os.environ.get('RESULTS_PATH', '/app/results/benchmarks'))
results = []

# Load all result files
for result_file in results_dir.glob('*_results.json'):
    with open(result_file) as f:
        results.append(json.load(f))

# Generate summary
summary = {
    'total_tests': len(results),
    'successful_tests': len([r for r in results if r['status'] == 'completed']),
    'failed_tests': len([r for r in results if r['status'] == 'failed']),
    'average_duration': sum(r['duration_seconds'] for r in results if r['status'] == 'completed') / max(1, len([r for r in results if r['status'] == 'completed'])),
    'results_by_method': {},
    'results_by_dataset': {}
}

# Group by method
for result in results:
    method = result['method']
    if method not in summary['results_by_method']:
        summary['results_by_method'][method] = []
    summary['results_by_method'][method].append(result)

# Group by dataset
for result in results:
    dataset = result['dataset']
    if dataset not in summary['results_by_dataset']:
        summary['results_by_dataset'][dataset] = []
    summary['results_by_dataset'][dataset].append(result)

# Save summary
with open(results_dir / 'benchmark_summary.json', 'w') as f:
    json.dump(summary, f, indent=2)

print(f"✅ Benchmark complete!")
print(f"   Total tests: {summary['total_tests']}")
print(f"   Successful: {summary['successful_tests']}")
print(f"   Failed: {summary['failed_tests']}")
print(f"   Average duration: {summary['average_duration']:.1f}s")
print(f"   Results saved to: {results_dir}/benchmark_summary.json")
EOF

echo ""
echo "🎉 Benchmarking complete! Check the results in $RESULTS_PATH"
