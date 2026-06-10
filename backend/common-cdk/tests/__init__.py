import os
import sys

# common-cdk is the package root when running pytest from backend/common-cdk
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
