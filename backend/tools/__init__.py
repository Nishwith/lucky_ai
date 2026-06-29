# Lucky AI — Tool Registry and Execution Package
# Importing all execution modules triggers decorators and registers tools automatically.

from backend.tools.registry import tool_registry, tool
from backend.tools.file_ops import *
from backend.tools.terminal import *
from backend.tools.code_runner import *
from backend.tools.project_scaffold import *
