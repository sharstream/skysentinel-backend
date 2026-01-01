#!/usr/bin/env python3
"""
FastMCP Compatibility Checker
Run before upgrading to identify breaking changes

Checks:
- Installed FastMCP version
- Deprecated API usage
- Known breaking changes in v3
- Provides upgrade recommendations
"""
import sys
import importlib.util
from typing import List, Dict


def check_fastmcp_version():
    """Check installed FastMCP version"""
    try:
        import fastmcp
        return fastmcp.__version__
    except ImportError:
        return None
    except AttributeError:
        return "unknown"


def check_deprecated_apis():
    """Check if we're using any deprecated FastMCP APIs"""
    warnings = []
    
    # Check for deprecated imports (update based on actual deprecations)
    deprecated_imports = [
        ('fastmcp.server.fastmcp', 'Use "from fastmcp import FastMCP" instead'),
        ('mcp.server.fastmcp', 'FastMCP 1.0 import - use "from fastmcp import FastMCP"'),
    ]
    
    for module_path, suggestion in deprecated_imports:
        spec = importlib.util.find_spec(module_path)
        if spec is not None:
            warnings.append({
                'type': 'deprecated_import',
                'module': module_path,
                'suggestion': suggestion
            })
    
    return warnings


def check_breaking_changes():
    """Check for known breaking changes in v3"""
    issues = []
    
    # This will be populated as v3 breaking changes are announced
    # Example structure for future updates:
    breaking_changes = [
        # {
        #     'feature': 'tool decorator signature',
        #     'v2_pattern': '@mcp.tool()',
        #     'v3_pattern': '@mcp.tool(name="...", description="...")',
        #     'affected_files': ['src/mcp_server/server.py']
        # }
    ]
    
    for change in breaking_changes:
        issues.append(change)
    
    return issues


def check_adapter_implementation():
    """Check if MCP adapter is properly implemented"""
    try:
        from src.mcp_server.mcp_adapter import get_mcp_adapter, FASTMCP_MAJOR_VERSION
        
        adapter = get_mcp_adapter()
        
        return {
            'status': 'ok',
            'adapter_version': FASTMCP_MAJOR_VERSION,
            'adapter_type': adapter.__class__.__name__
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


def run_compatibility_check():
    """Run full compatibility check"""
    print("=" * 60)
    print("FastMCP Compatibility Check")
    print("=" * 60)
    
    # Check version
    version = check_fastmcp_version()
    print(f"\n📦 Installed Version: {version or 'NOT INSTALLED'}")
    
    if not version:
        print("❌ FastMCP not installed!")
        print("   Install with: pip install fastmcp>=2.11.0,<3.0.0")
        return False
    
    if version.startswith('3.'):
        print("⚠️  FastMCP 3.x detected - review migration guide")
        print("   https://gofastmcp.com/development/upgrade-guide")
    elif version.startswith('2.'):
        print("✅ FastMCP 2.x - stable version")
    else:
        print(f"⚠️  Unknown version format: {version}")
    
    # Check adapter
    print("\n🔧 MCP Adapter:")
    adapter_status = check_adapter_implementation()
    if adapter_status['status'] == 'ok':
        print(f"✅ Adapter working: {adapter_status['adapter_type']}")
        print(f"   Version compatibility: v{adapter_status['adapter_version']}.x")
    else:
        print(f"❌ Adapter error: {adapter_status['error']}")
    
    # Check deprecated APIs
    print("\n🔍 Deprecated API Usage:")
    warnings = check_deprecated_apis()
    if warnings:
        print(f"⚠️  Found {len(warnings)} deprecated API usage(s):")
        for warn in warnings:
            print(f"   • {warn['module']}")
            print(f"     → {warn['suggestion']}")
    else:
        print("✅ No deprecated APIs detected")
    
    # Check breaking changes
    print("\n💥 Breaking Changes:")
    issues = check_breaking_changes()
    if issues:
        print(f"❌ Found {len(issues)} potential breaking change(s):")
        for issue in issues:
            print(f"\n   Feature: {issue['feature']}")
            print(f"   V2 Pattern: {issue['v2_pattern']}")
            print(f"   V3 Pattern: {issue['v3_pattern']}")
            print(f"   Affected: {', '.join(issue['affected_files'])}")
    else:
        print("✅ No known breaking changes detected")
    
    # Recommendations
    print("\n" + "=" * 60)
    print("📋 Recommendations:")
    print("=" * 60)
    
    if version and version.startswith('3.'):
        print("⚠️  You are using FastMCP 3.x:")
        print("   1. Review the v3 migration guide")
        print("   2. Run full test suite: pytest tests/")
        print("   3. Check all MCP tools work correctly")
        print("   4. Verify progressive disclosure still functions")
        print("   5. Test agent message bus functionality")
    elif version and version.startswith('2.'):
        print("✅ You are using FastMCP 2.x (recommended):")
        print("   1. Maintain version pin: fastmcp>=2.11.0,<3.0.0")
        print("   2. Monitor for v3 announcements")
        print("   3. Run tests regularly: pytest tests/")
        print("   4. Keep adapter pattern in place for future migration")
    else:
        print("⚠️  Version status unclear:")
        print("   1. Verify installation: pip show fastmcp")
        print("   2. Reinstall if needed: pip install fastmcp>=2.11.0,<3.0.0")
    
    print("\n" + "=" * 60)
    
    return True


if __name__ == "__main__":
    success = run_compatibility_check()
    sys.exit(0 if success else 1)

