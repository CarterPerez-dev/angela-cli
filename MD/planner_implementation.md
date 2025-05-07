# Advanced Task Planner

## Overview

The Advanced Task Planner extends Angela CLI's orchestration capabilities with comprehensive support for complex step types, rich data flow between steps, and robust error handling.

This enhanced implementation allows Angela to execute sophisticated task plans that involve:

- **Code execution** (Python, JavaScript, Shell)
- **API calls** to external services
- **File operations** with proper permission checks
- **Decision trees** with conditional branching
- **Loops** for iterative processing
- **Variable flow** between steps
- **Error recovery** for resilient execution

## Core Components

### Enhanced Step Types

The Advanced Task Planner supports the following step types:

| Type | Description | Key Parameters |
|------|-------------|----------------|
| `COMMAND` | Execute shell commands | `command` |
| `CODE` | Execute code in various languages | `code`, `language` |
| `FILE` | Perform file operations | `file_path`, `file_content`, `operation` |
| `DECISION` | Branch execution based on conditions | `condition`, `true_branch`, `false_branch` |
| `API` | Make HTTP API calls | `api_url`, `api_method`, `api_params`, `api_payload` |
| `LOOP` | Iterate over a collection | `loop_items`, `loop_body` |

### Data Flow System

The data flow system enables passing information between steps through variables:

- Variables can be referenced in step parameters using `${variable_name}` syntax
- Each step can output variables that subsequent steps can access
- Step results are automatically available to later steps via `${result.step_id.field}` syntax
- Special variables like `loop_item` and `loop_index` are available in loop iterations

### Error Handling & Recovery

The system includes sophisticated error handling:

- Retry mechanism with configurable attempt limits
- Integration with `ErrorRecoveryManager` for intelligent recovery
- Transaction-based execution with rollback capability
- Comprehensive logging and error reporting

## Using Advanced Plans

### Creating an Advanced Plan

An advanced plan is defined using the `AdvancedTaskPlan` model:

```python
plan = AdvancedTaskPlan(
    id="my_plan_id",
    goal="Accomplish a complex task",
    description="A detailed description of the plan",
    steps={
        "step1": AdvancedPlanStep(
            id="step1",
            type=PlanStepType.COMMAND,
            description="First step",
            command="echo 'Hello World'",
            dependencies=[],
            estimated_risk=0
        ),
        "step2": AdvancedPlanStep(
            id="step2",
            type=PlanStepType.DECISION,
            description="Decide next action",
            condition="file exists /tmp/test.txt",
            true_branch=["step3a"],
            false_branch=["step3b"],
            dependencies=["step1"],
            estimated_risk=0
        ),
        # Additional steps...
    },
    entry_points=["step1"],  # Where execution begins
    context={}
)
```

### Executing an Advanced Plan

Plans can be executed through the task planner:

```python
result = await task_planner.execute_plan(
    plan, 
    dry_run=False,
    transaction_id="optional_transaction_id",
    initial_variables={"var1": "value1"}
)
```

The execution result contains information about:
- Overall success/failure
- Execution path taken
- Individual step results
- Variables at end of execution
- Total execution time

## Advanced Step Types in Detail

### CODE Step

Execute code in Python, JavaScript, or Shell:

```python
CodeStep = AdvancedPlanStep(
    id="run_code",
    type=PlanStepType.CODE,
    description="Calculate statistics",
    code="""
# Process data
data = [1, 2, 3, 4, 5]
result = sum(data) / len(data)
print(f"Average: {result}")
    """,
    language="python",
    dependencies=[],
    estimated_risk=1
)
```

The code execution environment:
- Runs in a sandboxed process
- Has access to a limited set of imports
- Can read variables from the execution context
- Returns stdout, stderr, and explicit result variables

### API Step

Make HTTP requests to external services:

```python
ApiStep = AdvancedPlanStep(
    id="call_api",
    type=PlanStepType.API,
    description="Get weather data",
    api_url="https://api.example.com/weather",
    api_method="GET",
    api_params={"city": "London"},
    api_headers={"Authorization": "Bearer ${api_token}"},
    timeout=30,
    dependencies=[],
    estimated_risk=1
)
```

Key features:
- Supports all HTTP methods
- JSON and form data handling
- Response parsing with automatic JSON detection
- Variable interpolation in URL, headers, and payload

### DECISION Step

Branch execution based on conditions:

```python
DecisionStep = AdvancedPlanStep(
    id="check_condition",
    type=PlanStepType.DECISION,
    description="Check if prerequisites are met",
    condition="variable result > 10",
    true_branch=["success_step"],
    false_branch=["fallback_step"],
    dependencies=["previous_step"],
    estimated_risk=0
)
```

Condition types:
- Simple variable comparisons (`variable x == y`)
- File existence checks (`file exists path/to/file`)
- Command success checks (`command success step_id`)
- Output content checks (`output contains pattern in step_id`)
- Custom code conditions using `condition_code` parameter

### LOOP Step

Iterate over collections with dedicated body steps:

```python
LoopStep = AdvancedPlanStep(
    id="process_items",
    type=PlanStepType.LOOP,
    description="Process each item in list",
    loop_items="range(1, 5)",
    loop_body=["process_item_step"],
    dependencies=["setup_step"],
    estimated_risk=1
)
```

Loop items can be:
- Range expressions (`range(start, end, step)`)
- File patterns (`files(*.txt)`)
- Variable references (`${my_list}`)
- JSON arrays
- Comma-separated lists

Within loop iterations, special variables are available:
- `loop_item`: Current item being processed
- `loop_index`: Zero-based index of current iteration
- `loop_first`: Boolean indicating if this is the first iteration
- `loop_last`: Boolean indicating if this is the last iteration

### FILE Step

Perform file operations with proper safety checks:

```python
FileStep = AdvancedPlanStep(
    id="save_results",
    type=PlanStepType.FILE,
    description="Save results to file",
    file_path="/tmp/results.txt",
    file_content="Results: ${step_results}",
    operation="write",
    dependencies=["calculation_step"],
    estimated_risk=1
)
```

Supported operations:
- `read`: Read file content
- `write`: Write content to file
- `delete`: Delete file or directory
- `copy`: Copy file from source to destination
- `move`: Move file from source to destination

## Data Flow Examples

### Referencing Variables in Parameters

```python
# Referencing a variable in a command
CommandStep = AdvancedPlanStep(
    id="use_variable",
    type=PlanStepType.COMMAND,
    description="Use a variable in command",
    command="grep '${search_pattern}' ${filename}",
    dependencies=["previous_step"],
    estimated_risk=0
)
```

### Accessing Step Results

```python
# Access result of a previous step
CodeStep = AdvancedPlanStep(
    id="process_results",
    type=PlanStepType.CODE,
    description="Process previous results",
    code="""
# Get data from previous step
previous_output = variables.get('step1_stdout', '')
line_count = len(previous_output.splitlines())
print(f"Lines: {line_count}")
result = line_count * 2  # Store as explicit result
""",
    dependencies=["step1"],
    estimated_risk=0
)
```

### Setting Output Variables

All step types automatically create output variables:

- `COMMAND` steps: `${step_id}_stdout`, `${step_id}_stderr`, `${step_id}_return_code`
- `CODE` steps: Variables set in code, plus `${step_id}_stdout`, `${step_id}_result`
- `API` steps: `${step_id}_status_code`, `${step_id}_response_text`, `${step_id}_response_json`
- `FILE` steps: `${step_id}_content` (read) or `${step_id}_message` (write/delete/copy/move)
- `DECISION` steps: `${step_id}_condition_result`, `${step_id}_next_branch`
- `LOOP` steps: `${step_id}_iterations`

## Integration with Angela CLI

The Advanced Task Planner is fully integrated with Angela's orchestration system:

- Natural language requests can generate Advanced Task Plans automatically
- The terminal formatter provides rich visualization of plans and results
- Full transaction support with rollback capability
- Error recovery and retry mechanisms seamlessly applied

### Example of Natural Language Usage

```
$ angela "Download sales data from our API, extract monthly figures, calculate growth rates, and generate a summary report"
```

This will analyze the request complexity, create an Advanced Task Plan with appropriate steps, display the plan for confirmation, and execute it with full data flow and error handling.

## Best Practices

1. **Plan Structure**
   - Keep steps small and focused on a single task
   - Use meaningful step IDs and descriptions
   - Organize dependencies carefully to maintain a clear execution flow

2. **Data Flow**
   - Use explicit variable names for clarity
   - Consider creating "collector" steps that format and organize data
   - Be cautious with large variable values to avoid performance issues

3. **Error Handling**
   - Set appropriate retry values for steps that might temporarily fail
   - Consider adding fallback branches in decision steps
   - Use timeout parameters for external operations

4. **Security**
   - Set appropriate risk levels for steps
   - Avoid hardcoding sensitive information in steps
   - Use variable substitution for secure values

5. **Performance**
   - Batch operations when possible in loops
   - Consider using CODE steps for complex data processing instead of multiple COMMAND steps
   - Use dry runs for testing complex plans before actual execution

## Advanced Examples

### Complex Data Processing Pipeline

```python
plan = AdvancedTaskPlan(
    id="data_processing_pipeline",
    goal="Process sales data and generate reports",
    description="Download sales data, extract insights, and create reports",
    steps={
        "step1": AdvancedPlanStep(
            id="step1",
            type=PlanStepType.COMMAND,
            description="Download sales data",
            command="curl -s -o sales_data.csv https://example.com/api/sales",
            dependencies=[],
            estimated_risk=1
        ),
        "step2": AdvancedPlanStep(
            id="step2",
            type=PlanStepType.CODE,
            description="Parse and analyze CSV data",
            code="""
import csv
import statistics

sales_by_month = {}

with open('sales_data.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        month = row['month']
        sales = float(row['sales'])
        if month not in sales_by_month:
            sales_by_month[month] = []
        sales_by_month[month].append(sales)

# Calculate monthly statistics
monthly_stats = {}
for month, sales in sales_by_month.items():
    monthly_stats[month] = {
        'total': sum(sales),
        'average': statistics.mean(sales),
        'median': statistics.median(sales)
    }

# Store as result
result = monthly_stats
print(f"Processed {len(sales_by_month)} months of data")
            """,
            dependencies=["step1"],
            estimated_risk=0,
            language="python"
        ),
        "step3": AdvancedPlanStep(
            id="step3",
            type=PlanStepType.DECISION,
            description="Check if we have enough data",
            condition="variable step2_result.keys().length >= 3",
            condition_type="code",
            condition_code="""
# Check if we have at least 3 months of data
stats = variables.get('step2_result', {})
result = len(stats.keys()) >= 3
            """,
            true_branch=["step4a"],
            false_branch=["step4b"],
            dependencies=["step2"],
            estimated_risk=0
        ),
        "step4a": AdvancedPlanStep(
            id="step4a",
            type=PlanStepType.FILE,
            description="Generate full report",
            file_path="sales_report.md",
            file_content="""# Sales Report

## Monthly Statistics

${step2_result}

Generated on ${current_date}
            """,
            operation="write",
            dependencies=["step3"],
            estimated_risk=1
        ),
        "step4b": AdvancedPlanStep(
            id="step4b",
            type=PlanStepType.COMMAND,
            description="Notify about insufficient data",
            command="echo 'Insufficient data for full report' > notification.txt",
            dependencies=["step3"],
            estimated_risk=0
        )
    },
    entry_points=["step1"],
    context={}
)
```

### Web API Interaction with Error Handling

```python
plan = AdvancedTaskPlan(
    id="api_interaction",
    goal="Fetch and process user data",
    description="Query an API for user data and process the results",
    steps={
        "step1": AdvancedPlanStep(
            id="step1",
            type=PlanStepType.API,
            description="Fetch user list from API",
            api_url="https://api.example.com/users",
            api_method="GET",
            api_headers={
                "Authorization": "Bearer ${api_token}",
                "Content-Type": "application/json"
            },
            timeout=30,
            retry=3,  # Retry up to 3 times
            dependencies=[],
            estimated_risk=1
        ),
        "step2": AdvancedPlanStep(
            id="step2",
            type=PlanStepType.DECISION,
            description="Check API response",
            condition="variable step1_status_code == 200",
            true_branch=["step3"],
            false_branch=["step_error"],
            dependencies=["step1"],
            estimated_risk=0
        ),
        "step3": AdvancedPlanStep(
            id="step3",
            type=PlanStepType.LOOP,
            description="Process each user",
            loop_items="${step1_response_json.users}",
            loop_body=["step4"],
            dependencies=["step2"],
            estimated_risk=0
        ),
        "step4": AdvancedPlanStep(
            id="step4",
            type=PlanStepType.CODE,
            description="Process user info",
            code="""
# Get the current user from loop
user = variables.get('loop_item', {})
user_id = user.get('id')
name = user.get('name')

# Process user data
print(f"Processing user {name} (ID: {user_id})")

# Return structured result
result = {
    'id': user_id,
    'name': name,
    'processed': True,
    'timestamp': datetime.datetime.now().isoformat()
}
            """,
            language="python",
            dependencies=[],
            estimated_risk=0
        ),
        "step_error": AdvancedPlanStep(
            id="step_error",
            type=PlanStepType.FILE,
            description="Log API error",
            file_path="api_error.log",
            file_content="API Error: Status ${step1_status_code}\nResponse: ${step1_response_text}",
            operation="write",
            dependencies=["step2"],
            estimated_risk=1
        )
    },
    entry_points=["step1"],
    context={}
)
```

## Conclusion

The Advanced Task Planner represents a significant enhancement to Angela CLI's capabilities, enabling true autonomous task orchestration with comprehensive error handling and rich data flow. It transforms Angela from a simple command suggestion tool into a powerful automation platform capable of executing complex tasks with minimal user intervention.

Key benefits include:

- **Enhanced autonomy** - Angela can now handle complex multi-step operations with branching logic
- **Improved reliability** - Comprehensive error handling and recovery ensures robust execution
- **Greater flexibility** - Support for code execution, API calls, and iterative processing
- **Better context awareness** - Rich data flow between steps maintains context across the execution pipeline

These capabilities enable advanced use cases including:
- Complex data pipelines
- Multi-service integrations
- Automated troubleshooting with fallback paths
- Dynamic workflow execution based on real-time conditions


"""
Advanced Task Planner Usage Example

This module demonstrates practical usage of the enhanced Advanced Task Planner
with various step types, data flow, and error handling.
"""
import asyncio
import os
import uuid
import json
from pathlib import Path

from angela.intent.planner import (
    task_planner, TaskPlan, PlanStep, 
    AdvancedTaskPlan, AdvancedPlanStep, PlanStepType
)
from angela.shell.formatter import terminal_formatter
from angela.utils.logging import get_logger

logger = get_logger(__name__)

async def demo_advanced_plan():
    """Run a demonstration of an advanced task plan."""
    print("🚀 Starting Advanced Task Planner Demo")
    print("=======================================\n")
    
    # Create an advanced plan for data processing
    plan = create_data_processing_plan()
    
    # Display the plan
    await terminal_formatter.display_advanced_plan(plan)
    
    # Ask for confirmation
    print("\nExecute this plan? (y/n) ", end="")
    response = input().lower()
    
    if response.startswith('y'):
        # Execute the plan
        print("\n📋 Executing Advanced Plan...")
        result = await task_planner.execute_plan(
            plan, 
            dry_run=False,
            initial_variables={
                "data_dir": "./data",
                "output_dir": "./output",
                "min_temperature": 0,
                "max_temperature": 100
            }
        )
        
        # Display execution results
        await terminal_formatter.display_execution_results(plan, result)
        
        # Summarize the results
        if result["success"]:
            print("\n✅ Plan executed successfully!")
            
            # Show the final output if available
            if os.path.exists("./output/report.md"):
                print("\n📄 Generated Report Content:")
                with open("./output/report.md", "r") as f:
                    print(f.read())
        else:
            print("\n❌ Plan execution failed!")
            failed_step = result.get("failed_step")
            if failed_step and failed_step in result.get("results", {}):
                error = result["results"][failed_step].get("error", "Unknown error")
                print(f"\nFailed at step '{failed_step}': {error}")
    else:
        print("\nPlan execution cancelled.")

def create_data_processing_plan() -> AdvancedTaskPlan:
    """
    Create an advanced task plan for processing weather data.
    
    This demonstrates multiple step types, data flow, and error handling.
    
    Returns:
        AdvancedTaskPlan: The complete plan
    """
    plan_id = f"data_processing_{uuid.uuid4().hex[:8]}"
    
    return AdvancedTaskPlan(
        id=plan_id,
        goal="Process weather data and generate a report",
        description="A plan to download, analyze, and visualize weather data",
        steps={
            # Step 1: Set up directories
            "setup_dirs": AdvancedPlanStep(
                id="setup_dirs",
                type=PlanStepType.CODE,
                description="Set up data and output directories",
                code="""
# Create data and output directories if they don't exist
import os

data_dir = variables.get('data_dir', './data')
output_dir = variables.get('output_dir', './output')

os.makedirs(data_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

print(f"Created directories: {data_dir}, {output_dir}")
result = {"data_dir": data_dir, "output_dir": output_dir}
                """,
                dependencies=[],
                estimated_risk=1,
                language="python"
            ),
            
            # Step 2: Download sample data
            "download_data": AdvancedPlanStep(
                id="download_data",
                type=PlanStepType.COMMAND,
                description="Generate sample weather data",
                command="""
# Generate sample weather data CSV
cat > ${data_dir}/weather_data.csv << EOL
date,location,temperature,humidity,conditions
2023-01-01,New York,32,65,Snowing
2023-01-02,New York,35,60,Cloudy
2023-01-03,New York,28,70,Snowing
2023-01-01,Los Angeles,68,45,Sunny
2023-01-02,Los Angeles,72,40,Sunny
2023-01-03,Los Angeles,70,50,Partly Cloudy
2023-01-01,Chicago,18,70,Snowing
2023-01-02,Chicago,22,65,Snowing
2023-01-03,Chicago,25,60,Cloudy
EOL
""",
                dependencies=["setup_dirs"],
                estimated_risk=1
            ),
            
            # Step 3: Validate data file exists
            "check_data": AdvancedPlanStep(
                id="check_data",
                type=PlanStepType.DECISION,
                description="Check if data file exists",
                condition="file exists ${data_dir}/weather_data.csv",
                true_branch=["analyze_data"],
                false_branch=["handle_missing_data"],
                dependencies=["download_data"],
                estimated_risk=0
            ),
            
            # Step 4: Handle missing data (recovery path)
            "handle_missing_data": AdvancedPlanStep(
                id="handle_missing_data",
                type=PlanStepType.COMMAND,
                description="Generate fallback data if download failed",
                command="""
echo "date,location,temperature,humidity,conditions" > ${data_dir}/weather_data.csv
echo "2023-01-01,Fallback,50,50,Cloudy" >> ${data_dir}/weather_data.csv
""",
                dependencies=["check_data"],
                estimated_risk=1
            ),
            
            # Step 5: Analyze data
            "analyze_data": AdvancedPlanStep(
                id="analyze_data",
                type=PlanStepType.CODE,
                description="Analyze weather data",
                code="""
# Analyze weather data file
import csv
from statistics import mean

data_dir = variables.get('data_dir', './data')
min_temp = variables.get('min_temperature', 0)
max_temp = variables.get('max_temperature', 100)

# Initialize data structures
locations = {}
dates = set()
all_temps = []

# Read the CSV file
with open(f"{data_dir}/weather_data.csv", 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        location = row['location']
        temp = float(row['temperature'])
        date = row['date']
        
        # Filter by temperature range
        if min_temp <= temp <= max_temp:
            # Add to locations
            if location not in locations:
                locations[location] = {'temperatures': [], 'conditions': []}
            
            locations[location]['temperatures'].append(temp)
            locations[location]['conditions'].append(row['conditions'])
            
            # Add to all temps
            all_temps.append(temp)
            
            # Add to dates
            dates.add(date)

# Calculate statistics
location_stats = {}
for location, data in locations.items():
    avg_temp = mean(data['temperatures']) if data['temperatures'] else 0
    most_common_condition = max(set(data['conditions']), key=data['conditions'].count)
    location_stats[location] = {
        'avg_temperature': round(avg_temp, 1),
        'most_common_condition': most_common_condition,
        'samples': len(data['temperatures'])
    }

overall_stats = {
    'total_locations': len(locations),
    'total_dates': len(dates),
    'avg_temperature': round(mean(all_temps), 1) if all_temps else 0,
    'min_temperature': min(all_temps) if all_temps else 0,
    'max_temperature': max(all_temps) if all_temps else 0
}

# Store results
result = {
    'location_stats': location_stats,
    'overall_stats': overall_stats
}

print(f"Analyzed data for {len(locations)} locations across {len(dates)} dates")
print(f"Overall average temperature: {overall_stats['avg_temperature']}°F")
                """,
                dependencies=["check_data", "handle_missing_data"],
                estimated_risk=0,
                language="python"
            ),
            
            # Step 6: Check if we have enough data
            "check_analysis": AdvancedPlanStep(
                id="check_analysis",
                type=PlanStepType.DECISION,
                description="Check if analysis found enough data",
                condition="variable analyze_data_result.overall_stats.total_locations > 0",
                true_branch=["process_locations"],
                false_branch=["generate_error_report"],
                dependencies=["analyze_data"],
                estimated_risk=0
            ),
            
            # Step 7: Process each location
            "process_locations": AdvancedPlanStep(
                id="process_locations",
                type=PlanStepType.LOOP,
                description="Process each location",
                loop_items="${Object.keys(analyze_data_result.location_stats)}",
                loop_body=["process_location"],
                dependencies=["check_analysis"],
                estimated_risk=0
            ),
            
            # Step 8: Process a single location
            "process_location": AdvancedPlanStep(
                id="process_location",
                type=PlanStepType.CODE,
                description="Process a single location",
                code="""
# Process a single location
location = variables.get('loop_item')
location_stats = variables.get('analyze_data_result', {}).get('location_stats', {}).get(location, {})
output_dir = variables.get('output_dir', './output')

# Generate markdown for this location
markdown = f"""# Weather Report for {location}

## Statistics
- Average Temperature: {location_stats.get('avg_temperature')}°F
- Most Common Condition: {location_stats.get('most_common_condition')}
- Number of Samples: {location_stats.get('samples')}

Generated on: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

# Write to file
output_file = f"{output_dir}/{location.lower().replace(' ', '_')}_report.md"
with open(output_file, 'w') as f:
    f.write(markdown)

print(f"Generated report for {location}: {output_file}")
result = {
    "location": location,
    "output_file": output_file,
    "avg_temperature": location_stats.get('avg_temperature')
}
                """,
                language="python",
                dependencies=[],
                estimated_risk=1
            ),
            
            # Step 9: Generate summary report with API data
            "fetch_weather_icon": AdvancedPlanStep(
                id="fetch_weather_icon",
                type=PlanStepType.API,
                description="Fetch weather icon data",
                api_url="https://httpbin.org/anything",
                api_method="POST",
                api_payload={
                    "request_type": "weather_icons",
                    "conditions": ["Sunny", "Cloudy", "Snowing", "Partly Cloudy"]
                },
                dependencies=["process_locations"],
                estimated_risk=1
            ),
            
            # Step 10a: Generate final report
            "generate_report": AdvancedPlanStep(
                id="generate_report",
                type=PlanStepType.FILE,
                description="Generate final summary report",
                file_path="${output_dir}/report.md",
                file_content="""# Weather Analysis Report

## Overview
- Locations Analyzed: ${analyze_data_result.overall_stats.total_locations}
- Dates Covered: ${analyze_data_result.overall_stats.total_dates}
- Overall Average Temperature: ${analyze_data_result.overall_stats.avg_temperature}°F
- Temperature Range: ${analyze_data_result.overall_stats.min_temperature}°F to ${analyze_data_result.overall_stats.max_temperature}°F

## Location Summaries
${Object.entries(analyze_data_result.location_stats).map(([location, stats]) => 
  `### ${location}
  - Average Temperature: ${stats.avg_temperature}°F
  - Most Common Condition: ${stats.most_common_condition}
  - Samples: ${stats.samples}`
).join('\n\n')}

## API Integration Status
- Weather Icon API Status: ${fetch_weather_icon_status_code}

Report generated on: ${new Date().toISOString()}
""",
                operation="write",
                dependencies=["fetch_weather_icon"],
                estimated_risk=1
            ),
            
            # Step 10b: Generate error report
            "generate_error_report": AdvancedPlanStep(
                id="generate_error_report",
                type=PlanStepType.FILE,
                description="Generate error report",
                file_path="${output_dir}/error_report.md",
                file_content="""# Weather Analysis Error Report

No valid data was found for analysis. Please check the data source.

Error details:
- Data directory: ${setup_dirs_result.data_dir}
- Analysis result: ${JSON.stringify(analyze_data_result)}

Report generated on: ${new Date().toISOString()}
""",
                operation="write",
                dependencies=["check_analysis"],
                estimated_risk=1
            )
        },
        entry_points=["setup_dirs"],
        context={}
    )

# Run the demo if executed directly
if __name__ == "__main__":
    asyncio.run(demo_advanced_plan())
