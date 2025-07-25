#!/usr/bin/env python3
"""
Comprehensive performance test for FastIntercom MCP
Uses the existing integration test infrastructure with performance monitoring
"""

import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import psutil


def get_test_workspace() -> Path:
    """Get the test workspace directory with organized subdirectories."""
    # Check environment variable first
    if workspace_env := os.environ.get("FASTINTERCOM_TEST_WORKSPACE"):
        workspace = Path(workspace_env)
    else:
        # Find project root (look for pyproject.toml)
        current_dir = Path.cwd()
        project_root = current_dir

        # Search up the directory tree for pyproject.toml
        while current_dir != current_dir.parent:
            if (current_dir / "pyproject.toml").exists():
                project_root = current_dir
                break
            current_dir = current_dir.parent

        workspace = project_root / ".test-workspace"

    # Create organized subdirectories
    workspace.mkdir(exist_ok=True)
    (workspace / "data").mkdir(exist_ok=True)
    (workspace / "logs").mkdir(exist_ok=True)
    (workspace / "results").mkdir(exist_ok=True)

    return workspace


def monitor_system_resources():
    """Get current system resource usage"""
    process = psutil.Process()
    return {
        "memory_mb": process.memory_info().rss / 1024 / 1024,
        "cpu_percent": process.cpu_percent(),
        "timestamp": time.time(),
    }


def run_timed_test(command, description):
    """Run a command with timing and resource monitoring"""
    print(f"🔄 {description}...")

    start_time = time.time()
    start_resources = monitor_system_resources()

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        end_time = time.time()
        end_resources = monitor_system_resources()

        duration = end_time - start_time
        peak_memory = max(start_resources["memory_mb"], end_resources["memory_mb"])

        success = result.returncode == 0

        print(f"{'✅' if success else '❌'} {description} - {duration:.2f}s, {peak_memory:.1f}MB")

        if not success:
            print(f"  Error: {result.stderr}")

        return {
            "success": success,
            "duration": duration,
            "peak_memory_mb": peak_memory,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    except subprocess.TimeoutExpired:
        print(f"❌ {description} - TIMEOUT after 5 minutes")
        return {
            "success": False,
            "duration": 300,
            "peak_memory_mb": 0,
            "stdout": "",
            "stderr": "Timeout after 5 minutes",
        }


def check_database_metrics(db_path):
    """Check database size and conversation count"""
    if not Path(db_path).exists():
        return {"size_mb": 0, "conversations": 0, "messages": 0}

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get conversation count
        cursor.execute("SELECT COUNT(*) FROM conversations")
        conversations = cursor.fetchone()[0]

        # Get message count
        cursor.execute("SELECT COUNT(*) FROM messages")
        messages = cursor.fetchone()[0]

        conn.close()

        # Get file size
        size_mb = Path(db_path).stat().st_size / 1024 / 1024

        return {
            "size_mb": size_mb,
            "conversations": conversations,
            "messages": messages,
        }

    except Exception as e:
        print(f"⚠️ Database check error: {e}")
        return {"size_mb": 0, "conversations": 0, "messages": 0}


def test_environment():
    """Test basic environment setup"""
    print("🔧 Testing environment...")

    # Check Python imports
    import_test = run_timed_test(
        "python3 -c \"import fast_intercom_mcp; print('✅ Import successful')\"",
        "Module import test",
    )

    # Check CLI availability
    cli_test = run_timed_test("python3 -m fast_intercom_mcp --help", "CLI availability test")

    # Check token availability
    token_available = bool(os.environ.get("INTERCOM_ACCESS_TOKEN"))
    token_status = "available" if token_available else "missing"
    icon = "✅" if token_available else "❌"
    print(f"{icon} API token {token_status}")

    return import_test["success"] and cli_test["success"] and token_available


def run_integration_test_with_monitoring():
    """Run the integration test with comprehensive monitoring"""
    print("🚀 Running integration test with performance monitoring...")

    # Setup test environment using standardized workspace
    workspace = get_test_workspace()
    test_db_path = workspace / "data" / "data.db"

    # Remove existing test database for clean test
    if test_db_path.exists():
        test_db_path.unlink()

    # Run integration test
    os.environ["FASTINTERCOM_CONFIG_DIR"] = str(workspace / "data")
    os.environ["FASTINTERCOM_TEST_WORKSPACE"] = str(workspace)

    integration_result = run_timed_test(
        "./scripts/run_integration_test.sh --days 7 --max-conversations 500",
        "Integration test (7 days, 500 conversations max)",
    )

    # Check final database metrics
    db_metrics = check_database_metrics(test_db_path)

    return integration_result, db_metrics


def test_server_startup():
    """Test MCP server startup performance"""
    print("🖥️ Testing MCP server startup...")

    # Test server help (quick startup test)
    return run_timed_test(
        "timeout 10s python3 -m fast_intercom_mcp server --help", "Server help command"
    )


def calculate_efficiency_metrics(integration_result, db_metrics):
    """Calculate efficiency metrics from test results"""
    conversations = db_metrics["conversations"]
    duration = integration_result["duration"]
    db_size = db_metrics["size_mb"]
    memory = integration_result["peak_memory_mb"]

    return {
        "sync_rate_conversations_per_second": conversations / max(duration, 1),
        "storage_efficiency_conversations_per_mb": conversations / max(db_size, 0.1),
        "memory_efficiency_conversations_per_mb_ram": conversations / max(memory, 1),
        "database_efficiency_kb_per_conversation": (db_size * 1024) / max(conversations, 1),
    }


def generate_performance_report(test_results):
    """Generate comprehensive performance report"""
    workspace = get_test_workspace()

    report = {
        "test_info": {
            "timestamp": datetime.now().isoformat(),
            "python_version": sys.version,
            "platform": sys.platform,
            "working_directory": os.getcwd(),
            "test_workspace": str(workspace),
        },
        "test_results": test_results,
        "summary": {
            "overall_success": all(
                result.get("success", False)
                for result in test_results.values()
                if isinstance(result, dict) and "success" in result
            ),
        },
    }

    # Add performance assessment
    if "integration_test" in test_results and "db_metrics" in test_results:
        integration = test_results["integration_test"]
        db_metrics = test_results["db_metrics"]

        if integration["success"] and db_metrics["conversations"] > 0:
            efficiency = calculate_efficiency_metrics(integration, db_metrics)
            report["performance_metrics"] = efficiency

            # Performance rating
            score = 0
            if efficiency["sync_rate_conversations_per_second"] >= 10:
                score += 2
            elif efficiency["sync_rate_conversations_per_second"] >= 5:
                score += 1

            if integration["peak_memory_mb"] <= 100:
                score += 2
            elif integration["peak_memory_mb"] <= 200:
                score += 1

            if integration["duration"] <= 60:
                score += 2
            elif integration["duration"] <= 120:
                score += 1

            rating = (
                "EXCELLENT"
                if score >= 5
                else "GOOD"
                if score >= 3
                else "FAIR"
                if score >= 1
                else "NEEDS_IMPROVEMENT"
            )
            report["summary"]["performance_rating"] = rating

    return report


def main():
    print("🚀 FastIntercom MCP Comprehensive Performance Test")
    print("=" * 60)

    # Navigate to project directory
    os.chdir("/Users/chris-home/Developer/fast-intercom-mcp")

    test_results = {}

    # Test 1: Environment
    print("\n1. Environment Test")
    test_results["environment_ready"] = test_environment()

    if not test_results["environment_ready"]:
        print("❌ Environment test failed - cannot continue")
        return 1

    # Test 2: Server startup
    print("\n2. Server Startup Test")
    test_results["server_startup"] = test_server_startup()

    # Test 3: Integration test with monitoring
    print("\n3. Integration Test with Performance Monitoring")
    integration_result, db_metrics = run_integration_test_with_monitoring()
    test_results["integration_test"] = integration_result
    test_results["db_metrics"] = db_metrics

    # Generate and save report
    report = generate_performance_report(test_results)
    workspace = get_test_workspace()

    report_path = workspace / "results" / "performance_test_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    # Print summary
    print("\n" + "=" * 60)
    print("📊 PERFORMANCE TEST RESULTS")
    print("=" * 60)

    overall_success = report["summary"]["overall_success"]
    print(f"✅ Overall Status: {'PASSED' if overall_success else 'FAILED'}")

    if "performance_rating" in report["summary"]:
        print(f"🏆 Performance Rating: {report['summary']['performance_rating']}")

    print("\n📈 Test Results:")
    for test_name, result in test_results.items():
        if isinstance(result, dict) and "success" in result:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            duration = result.get("duration", 0)
            memory = result.get("peak_memory_mb", 0)
            print(f"  • {test_name}: {status} ({duration:.1f}s, {memory:.1f}MB)")
        elif isinstance(result, bool):
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  • {test_name}: {status}")

    if test_results.get("db_metrics", {}).get("conversations", 0) > 0:
        db = test_results["db_metrics"]
        print("\n💾 Database Metrics:")
        print(f"  • Conversations synced: {db['conversations']:,}")
        print(f"  • Messages synced: {db['messages']:,}")
        print(f"  • Database size: {db['size_mb']:.2f}MB")

        if "performance_metrics" in report:
            perf = report["performance_metrics"]
            print("\n⚡ Performance Metrics:")
            print(f"  • Sync rate: {perf['sync_rate_conversations_per_second']:.1f} conv/sec")
            print(
                f"  • Storage efficiency: "
                f"{perf['storage_efficiency_conversations_per_mb']:.1f} conv/MB"
            )
            print(
                f"  • Memory efficiency: "
                f"{perf['memory_efficiency_conversations_per_mb_ram']:.1f} conv/MB RAM"
            )
            print(
                f"  • Avg conversation size: "
                f"{perf['database_efficiency_kb_per_conversation']:.1f}KB"
            )

    print(f"\n📄 Full report saved to: {report_path.absolute()}")

    return 0 if overall_success else 1


if __name__ == "__main__":
    sys.exit(main())
