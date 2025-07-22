"""
Quick setup check for VESPA automation
Run this to verify everything is installed correctly
"""

import sys
import os

print("="*60)
print("VESPA Automation Setup Check")
print("="*60)

# Check Python version
print(f"\n1. Python Version: {sys.version}")
if sys.version_info < (3, 6):
    print("   ❌ Python 3.6+ required")
else:
    print("   ✓ Python version OK")

# Check required packages
print("\n2. Required Packages:")
packages_ok = True

try:
    import requests
    print("   ✓ requests installed")
except ImportError:
    print("   ❌ requests not installed - run: pip install requests")
    packages_ok = False

try:
    import numpy
    print("   ✓ numpy installed")
except ImportError:
    print("   ❌ numpy not installed - run: pip install numpy")
    packages_ok = False

# Check required files
print("\n3. Required Files:")
files_to_check = [
    'reverse_vespa_calculator.py',
    'knack_vespa_automation.py',
    'run_vespa_automation.py',
    'knack_config_example.py',
    'AIVESPACoach/psychometric_question_output_object_120.json',
    'AIVESPACoach/psychometric_question_details.json'
]

all_files_ok = True
for file in files_to_check:
    if os.path.exists(file):
        print(f"   ✓ {file}")
    else:
        print(f"   ❌ {file} - File not found!")
        all_files_ok = False

# Check for config file
print("\n4. Configuration:")
if os.path.exists('knack_config.py'):
    print("   ✓ knack_config.py exists")
    
    # Try to import and check if it's configured
    try:
        import knack_config as config
        if config.KNACK_APP_ID == "your-app-id-here":
            print("   ⚠️  knack_config.py needs to be configured with your API credentials")
        else:
            print("   ✓ knack_config.py appears to be configured")
    except Exception as e:
        print(f"   ⚠️  Error reading knack_config.py: {e}")
else:
    print("   ⚠️  knack_config.py not found")
    print("      Run: copy knack_config_example.py knack_config.py")
    print("      Then edit it with your Knack API credentials")

# Summary
print("\n" + "="*60)
print("Setup Summary:")
print("="*60)

if packages_ok and all_files_ok:
    print("\n✓ All requirements met!")
    print("\nNext steps:")
    
    if not os.path.exists('knack_config.py'):
        print("1. Create your config file:")
        print("   copy knack_config_example.py knack_config.py")
        print("2. Edit knack_config.py with your API credentials")
        print("3. Run: python reverse_vespa_calculator.py (to test calculator)")
        print("4. Run: python run_vespa_automation.py (to process students)")
    else:
        print("1. Test the calculator: python reverse_vespa_calculator.py")
        print("2. Run automation: python run_vespa_automation.py")
else:
    print("\n❌ Some requirements are missing. Please fix the issues above.")

print("\nFor detailed instructions, see TEST_LOCALLY_GUIDE.md") 