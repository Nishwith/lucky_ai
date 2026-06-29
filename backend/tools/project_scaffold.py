from pydantic import BaseModel
from typing import Literal
from backend.tools.registry import tool
from backend.tools.schemas import ToolResult
from backend.tools.file_ops import resolve_path

class ScaffoldInput(BaseModel):
    template: Literal["fastapi", "react", "html", "python"]
    project_name: str

@tool("scaffold_project", "Creates directory structure and starter template files inside the workspace.", "CONFIRM", ScaffoldInput)
def scaffold_project(template: str, project_name: str) -> ToolResult:
    try:
        # Resolve target project folder path relative to workspace
        proj_dir = resolve_path(project_name)
        if proj_dir.exists():
            return ToolResult(success=False, error=f"Folder '{project_name}' already exists.")
            
        proj_dir.mkdir(parents=True, exist_ok=True)
        
        # Build template
        if template == "fastapi":
            # 1. main.py
            with open(proj_dir / "main.py", "w", encoding="utf-8") as f:
                f.write('''from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World from Lucky AI scaffolded FastAPI app!"}
''')
            # 2. requirements.txt
            with open(proj_dir / "requirements.txt", "w", encoding="utf-8") as f:
                f.write("fastapi\nuvicorn\n")
            # 3. README.md
            with open(proj_dir / "README.md", "w", encoding="utf-8") as f:
                f.write(f"# {project_name}\n\nFastAPI project scaffolded by Lucky AI.\n")
                
        elif template == "react":
            # 1. package.json
            with open(proj_dir / "package.json", "w", encoding="utf-8") as f:
                f.write(f'''{{
  "name": "{project_name.lower()}",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {{
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  }},
  "dependencies": {{
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  }},
  "devDependencies": {{
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "vite": "^5.4.1"
  }}
}}''')
            # 2. index.html
            with open(proj_dir / "index.html", "w", encoding="utf-8") as f:
                f.write('''<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>React App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>''')
            # 3. src/ directory
            src_dir = proj_dir / "src"
            src_dir.mkdir(exist_ok=True)
            with open(src_dir / "main.jsx", "w", encoding="utf-8") as f:
                f.write('''import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)''')
            with open(src_dir / "App.jsx", "w", encoding="utf-8") as f:
                f.write('''import React from 'react'

function App() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', flexDirection: 'column' }}>
      <h1>React App Scaffolded Successfully!</h1>
      <p>Powered by Lucky AI OS</p>
    </div>
  )
}

export default App''')
            # 4. vite.config.js
            with open(proj_dir / "vite.config.js", "w", encoding="utf-8") as f:
                f.write('''import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})''')

        elif template == "html":
            # 1. index.html
            with open(proj_dir / "index.html", "w", encoding="utf-8") as f:
                f.write(f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name}</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <h1>Welcome to {project_name}!</h1>
        <p>Scaffolded by Lucky AI OS</p>
    </div>
    <script src="script.js"></script>
</body>
</html>''')
            # 2. style.css
            with open(proj_dir / "style.css", "w", encoding="utf-8") as f:
                f.write('''body {
    font-family: Arial, sans-serif;
    background-color: #f0f2f5;
    margin: 0;
    padding: 0;
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
}
.container {
    text-align: center;
    background: white;
    padding: 40px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}''')
            # 3. script.js
            with open(proj_dir / "script.js", "w", encoding="utf-8") as f:
                f.write('console.log("Static HTML site scaffolded by Lucky AI initialized!");')

        elif template == "python":
            # 1. main.py
            with open(proj_dir / "main.py", "w", encoding="utf-8") as f:
                f.write('''def main():
    print("Hello from Lucky AI python template script!")

if __name__ == "__main__":
    main()
''')
            # 2. README.md
            with open(proj_dir / "README.md", "w", encoding="utf-8") as f:
                f.write(f"# {project_name}\n\nPython script scaffolded by Lucky AI.\n")
                
        return ToolResult(success=True, output=f"Project '{project_name}' scaffolded successfully using '{template}' template.")
    except Exception as e:
        return ToolResult(success=False, error=str(e))
