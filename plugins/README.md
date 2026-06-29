# Lucky AI — Plugins Directory

This directory is the reserved location for installing additional plugins and system extension modules for LUCKY AI.

## Structure
Every plugin should be scaffolded inside its own subdirectory under this folder:
```
plugins/
  ├── my_custom_plugin/
  │     ├── __init__.py
  │     ├── manifest.json   # Optional manifest config
  │     └── tools.py        # Custom tool registrations using @tool decorator
```

## How It Works
LUCKY AI automatically imports and registers any tools declared using the standard `@tool` decorator. 
During the startup phase, the loader detects subdirectories inside this folder and mounts them to dynamically extend the system capability list.
