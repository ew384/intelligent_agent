#!/usr/bin/env python
# run_tests.py
"""
Script to run all tests sequentially and generate a report.
"""

import subprocess
import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime

# Test scripts
TESTS = [
    {
        "name": "Service Status Check",
        "script": "test_services.py",
        "timeout": 10  # seconds
    },
    {
        "name": "API Gateway Test",
        "script": "api-gateway-test.py",
        "timeout": 30
    },
    {
        "name": "Orchestrator Test",
        "script": "orchestrator-test.py",
        "timeout": 30
    },
    {
        "name": "Scenario Service Test",
        "script": "scenario-test.py",
        "timeout": 30
    },
    {
        "name": "Tool Service Test",
        "script": "tool-service-test.py",
        "timeout": 45
    },
    {
        "name": "Standalone Chrome-Selenium Test",
        "script": "browser-test.py",
        "timeout": 60
    },
    {
        "name": "Credit Card Handler Debug",
        "script": "credit-card-debug.py",
        "timeout": 120  # Longer timeout as it may need manual interaction
    }
]

def run_test(test):
    """Run a test script and capture its output"""
    print(f"\n===== Running: {test['name']} =====")
    start_time = time.time()
    
    try:
        # Run the test process
        process = subprocess.Popen(
            [sys.executable, test["script"]],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Wait for the process to complete or timeout
        try:
            stdout, _ = process.communicate(timeout=test["timeout"])
            exit_code = process.returncode
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, _ = process.communicate()
            exit_code = -1
            stdout += "\n\nTEST TIMED OUT!"
            
        elapsed_time = time.time() - start_time
        
        # Print output
        print(stdout)
        
        # Create result record
        result = {
            "name": test["name"],
            "script": test["script"],
            "exit_code": exit_code,
            "passed": exit_code == 0,
            "elapsed_time": round(elapsed_time, 2),
            "output": stdout
        }
        
        # Print status
        status = "✓ PASSED" if result["passed"] else "✗ FAILED"
        print(f"\n{status} in {result['elapsed_time']}s (exit code: {exit_code})")
        
        return result
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"Error running test: {str(e)}")
        return {
            "name": test["name"],
            "script": test["script"],
            "exit_code": -2,
            "passed": False,
            "elapsed_time": round(elapsed_time, 2),
            "output": f"Exception: {str(e)}"
        }

def create_report(results):
    """Create HTML report from test results"""
    # Create results directory
    reports_dir = Path("./test_reports")
    reports_dir.mkdir(exist_ok=True)
    
    # Create unique report filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = reports_dir / f"test_report_{timestamp}.html"
    
    # Calculate statistics
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r["passed"])
    failed_tests = total_tests - passed_tests
    pass_percentage = round((passed_tests / total_tests) * 100) if total_tests > 0 else 0
    
    # Create HTML content
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Intelligent Agent Test Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; }}
            h1 {{ color: #2c3e50; }}
            .summary {{ display: flex; margin-bottom: 20px; }}
            .summary-box {{ padding: 20px; margin-right: 20px; border-radius: 5px; color: white; }}
            .total {{ background-color: #3498db; }}
            .passed {{ background-color: #2ecc71; }}
            .failed {{ background-color: #e74c3c; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .status-passed {{ color: #2ecc71; font-weight: bold; }}
            .status-failed {{ color: #e74c3c; font-weight: bold; }}
            .output {{ max-height: 300px; overflow-y: auto; white-space: pre-wrap; background-color: #f8f8f8; padding: 10px; border-radius: 5px; }}
            .output-toggle {{ cursor: pointer; color: #3498db; }}
        </style>
        <script>
            function toggleOutput(id) {{
                const output = document.getElementById('output-' + id);
                if (output.style.display === 'none') {{
                    output.style.display = 'block';
                }} else {{
                    output.style.display = 'none';
                }}
            }}
        </script>
    </head>
    <body>
        <h1>Intelligent Agent Test Report</h1>
        <p>Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        
        <div class="summary">
            <div class="summary-box total">
                <h2>Total Tests</h2>
                <p>{total_tests}</p>
            </div>
            <div class="summary-box passed">
                <h2>Passed</h2>
                <p>{passed_tests} ({pass_percentage}%)</p>
            </div>
            <div class="summary-box failed">
                <h2>Failed</h2>
                <p>{failed_tests}</p>
            </div>
        </div>
        
        <h2>Test Results</h2>
        <table>
            <tr>
                <th>Test</th>
                <th>Status</th>
                <th>Duration</th>
                <th>Exit Code</th>
                <th>Output</th>
            </tr>
    """
    
    # Add rows for each test
    for i, result in enumerate(results):
        status_class = "passed" if result["passed"] else "failed"
        status_text = "PASSED" if result["passed"] else "FAILED"
        
        html += f"""
            <tr>
                <td>{result["name"]}</td>
                <td class="status-{status_class}">{status_text}</td>
                <td>{result["elapsed_time"]}s</td>
                <td>{result["exit_code"]}</td>
                <td>
                    <div class="output-toggle" onclick="toggleOutput({i})">Show/Hide Output</div>
                    <div id="output-{i}" class="output" style="display: none;">{result["output"]}</div>
                </td>
            </tr>
        """
    
    # Close the HTML
    html += """
        </table>
    </body>
    </html>
    """
    
    # Write the report
    with open(report_path, "w") as f:
        f.write(html)
    
    print(f"\nTest report saved to: {report_path}")
    return report_path

def save_json_results(results):
    """Save results to a JSON file for further processing"""
    reports_dir = Path("./test_reports")
    reports_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = reports_dir / f"test_results_{timestamp}.json"
    
    # Create a version of results suitable for JSON
    json_results = []
    for r in results:
        # Create a copy of the result without the full output (which might be long)
        json_result = r.copy()
        json_result["output_snippet"] = json_result["output"][:200] + "..." if len(json_result["output"]) > 200 else json_result["output"]
        json_results.append(json_result)
    
    with open(json_path, "w") as f:
        json.dump(json_results, f, indent=2)
    
    print(f"JSON results saved to: {json_path}")

def main():
    """Main function to run all tests"""
    print("Starting Intelligent Agent Test Suite")
    start_time = time.time()
    
    results = []
    for test in TESTS:
        results.append(run_test(test))
    
    # Create report
    elapsed_time = time.time() - start_time
    print(f"\nAll tests completed in {round(elapsed_time, 2)}s")
    
    # Print summary
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"\nTest Summary: {passed}/{total} tests passed")
    
    # Create HTML report
    report_path = create_report(results)
    
    # Save JSON results
    save_json_results(results)
    
    # Return success if all tests passed
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
