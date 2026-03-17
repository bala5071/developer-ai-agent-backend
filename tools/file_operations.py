import os
import json
import shutil
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Union
from datetime import datetime
from crewai.tools import tool


# File type categorization
FILE_CATEGORIES = {
    'source_code': {
        'python': ['.py', '.pyw', '.pyx'],
        'javascript': ['.js', '.mjs', '.cjs'],
        'typescript': ['.ts', '.tsx'],
        'java': ['.java'],
        'csharp': ['.cs', '.cshtml', '.razor'],
        'go': ['.go'],
        'rust': ['.rs'],
        'cpp': ['.cpp', '.cc', '.cxx', '.h', '.hpp'],
        'c': ['.c', '.h'],
        'ruby': ['.rb'],
        'php': ['.php'],
        'swift': ['.swift'],
        'kotlin': ['.kt', '.kts'],
        'scala': ['.scala'],
        'r': ['.r', '.R'],
        'matlab': ['.m'],
        'shell': ['.sh', '.bash', '.zsh', '.fish'],
        'powershell': ['.ps1', '.psm1'],
    },
    'markup': ['.html', '.htm', '.xml', '.svg'],
    'styling': ['.css', '.scss', '.sass', '.less', '.styl'],
    'data': ['.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf'],
    'documentation': ['.md', '.rst', '.txt', '.adoc', '.tex'],
    'database': ['.sql', '.db', '.sqlite', '.sqlite3'],
    'config': ['.env', '.gitignore', '.dockerignore', '.editorconfig'],
    'build': ['Makefile', 'Dockerfile', 'docker-compose.yml', '.gitlab-ci.yml'],
    'package': ['package.json', 'requirements.txt', 'Cargo.toml', 'go.mod', 'pom.xml', 'build.gradle'],
}

# Binary file extensions that should not be read as text
BINARY_EXTENSIONS = {
    '.pyc', '.pyo', '.so', '.dll', '.exe', '.bin', '.dat',
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg',
    '.mp3', '.mp4', '.avi', '.mov', '.wav',
    '.zip', '.tar', '.gz', '.bz2', '.7z', '.rar',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.class', '.jar', '.war', '.ear',
    '.wasm', '.o', '.a', '.lib'
}


def get_file_category(file_path: str) -> str:
    """Determine the category of a file"""
    path = Path(file_path)
    ext = path.suffix.lower()
    name = path.name
    
    # Check source code
    for lang, extensions in FILE_CATEGORIES['source_code'].items():
        if ext in extensions:
            return f'source_code/{lang}'
    
    # Check other categories
    for category, extensions in FILE_CATEGORIES.items():
        if category != 'source_code':
            if ext in extensions or name in extensions:
                return category
    
    return 'other'


def is_binary_file(file_path: str) -> bool:
    """Check if a file is binary"""
    ext = Path(file_path).suffix.lower()
    return ext in BINARY_EXTENSIONS


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


@tool("Write content to a file")
def write_file(file_path: str, content: str, mode: str = 'w', encoding: str = 'utf-8', 
               create_backup: bool = False) -> str:
    """
    Writes content to a file with advanced options.
    
    Args:
        file_path: Path to the file
        content: Content to write
        mode: Write mode ('w' for write, 'a' for append) (default: 'w')
        encoding: File encoding (default: 'utf-8')
        create_backup: Create backup of existing file before overwriting (default: False)
    
    Returns:
        Success message with file info or error message
    """
    try:
        path = Path(file_path)
        
        # Create backup if requested and file exists
        if create_backup and path.exists():
            backup_path = path.with_suffix(path.suffix + '.backup')
            shutil.copy2(path, backup_path)
        
        # Create parent directories
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        with open(path, mode, encoding=encoding) as f:
            f.write(content)
        
        # Get file info
        size = path.stat().st_size
        category = get_file_category(file_path)
        
        result = f"✓ Successfully wrote to: {file_path}\n"
        result += f"  Size: {format_file_size(size)}\n"
        result += f"  Category: {category}\n"
        result += f"  Mode: {'Append' if mode == 'a' else 'Write'}\n"
        result += f"  Lines: {len(content.splitlines())}"
        
        if create_backup:
            result += f"\n  Backup created: {backup_path}"
        
        return result
        
    except Exception as e:
        return f"✗ Error writing file {file_path}: {str(e)}"


@tool("Read content from a file")
def read_file(file_path: str, encoding: str = 'utf-8', max_lines: Optional[int] = None,
              start_line: int = 1) -> str:
    """
    Reads content from a file with advanced options.
    
    Args:
        file_path: Path to the file
        encoding: File encoding (default: 'utf-8')
        max_lines: Maximum number of lines to read (None for all)
        start_line: Line number to start reading from (1-indexed)
    
    Returns:
        File content or error message
    """
    try:
        path = Path(file_path)
        
        if not path.exists():
            return f"✗ Error: File does not exist: {file_path}"
        
        # Check if binary
        if is_binary_file(file_path):
            size = path.stat().st_size
            return f"⚠ Binary file detected: {file_path}\nSize: {format_file_size(size)}\nUse binary read operations for this file."
        
        # Read file
        with open(path, 'r', encoding=encoding) as f:
            lines = f.readlines()
        
        # Apply line filtering
        if start_line > 1:
            lines = lines[start_line - 1:]
        
        if max_lines:
            lines = lines[:max_lines]
        
        content = ''.join(lines)
        
        # Add file info header
        total_lines = len(Path(file_path).read_text(encoding=encoding).splitlines())
        size = path.stat().st_size
        category = get_file_category(file_path)
        
        header = f"File: {file_path}\n"
        header += f"Size: {format_file_size(size)} | Lines: {total_lines} | Category: {category}\n"
        header += "─" * 60 + "\n"
        
        if max_lines or start_line > 1:
            header += f"Showing lines {start_line}-{start_line + len(lines) - 1}\n"
            header += "─" * 60 + "\n"
        
        return header + content
        
    except UnicodeDecodeError:
        return f"✗ Error: Cannot decode file as text with {encoding} encoding. File may be binary."
    except Exception as e:
        return f"✗ Error reading file {file_path}: {str(e)}"


@tool("Append content to a file")
def append_to_file(file_path: str, content: str, add_newline: bool = True) -> str:
    """
    Appends content to an existing file or creates a new one.
    
    Args:
        file_path: Path to the file
        content: Content to append
        add_newline: Add newline before content if file exists (default: True)
    
    Returns:
        Success message or error message
    """
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Add newline if file exists and not empty
        if path.exists() and path.stat().st_size > 0 and add_newline:
            content = "\n" + content
        
        with open(path, 'a', encoding='utf-8') as f:
            f.write(content)
        
        size = path.stat().st_size
        return f"✓ Successfully appended to: {file_path}\n  New size: {format_file_size(size)}"
        
    except Exception as e:
        return f"✗ Error appending to file {file_path}: {str(e)}"


@tool("Create a directory")
def create_directory(directory_path: str, with_init: bool = False, 
                    init_content: str = "") -> str:
    """
    Creates a directory structure with optional initialization files.
    
    Args:
        directory_path: Path to the directory
        with_init: Create __init__.py (Python) or index file (default: False)
        init_content: Content for initialization file (default: empty)
    
    Returns:
        Success message with created items or error message
    """
    try:
        path = Path(directory_path)
        path.mkdir(parents=True, exist_ok=True)
        
        result = f"✓ Successfully created directory: {directory_path}"
        
        # Create initialization file if requested
        if with_init:
            # Detect if it's a Python project (has .py files in parent)
            parent_has_py = any(path.parent.glob('*.py'))
            
            if parent_has_py or '__pycache__' in str(directory_path):
                init_file = path / '__init__.py'
                with open(init_file, 'w', encoding='utf-8') as f:
                    f.write(init_content if init_content else '"""Package initialization."""\n')
                result += f"\n  Created: __init__.py"
            else:
                # For other languages, create index file
                init_file = path / 'index.js'  # Default to JS
                with open(init_file, 'w', encoding='utf-8') as f:
                    f.write(init_content if init_content else '// Module exports\n')
                result += f"\n  Created: index.js"
        
        return result
        
    except Exception as e:
        return f"✗ Error creating directory {directory_path}: {str(e)}"


@tool("List files in a directory")
def list_directory(directory_path: str = ".", pattern: str = "*", 
                   recursive: bool = True, show_hidden: bool = False,
                   categorize: bool = True, show_size: bool = True) -> str:
    """
    Lists files and directories with advanced filtering and organization.
    
    Args:
        directory_path: Path to the directory (default: current directory)
        pattern: File pattern to match (e.g., '*.py', '*.js') (default: '*')
        recursive: List files recursively (default: True)
        show_hidden: Show hidden files (starting with .) (default: False)
        categorize: Group files by category (default: True)
        show_size: Show file sizes (default: True)
    
    Returns:
        Formatted directory listing with stats or error message
    """
    try:
        path = Path(directory_path)
        
        if not path.exists():
            return f"✗ Error: Directory does not exist: {directory_path}"
        
        if not path.is_dir():
            return f"✗ Error: Not a directory: {directory_path}"
        
        # Collect files
        if recursive:
            items = list(path.rglob(pattern))
        else:
            items = list(path.glob(pattern))
        
        # Filter hidden files
        if not show_hidden:
            items = [item for item in items if not any(part.startswith('.') for part in item.parts)]
        
        # Separate files and directories
        files = [item for item in items if item.is_file()]
        dirs = [item for item in items if item.is_dir()]
        
        if not files and not dirs:
            return f"No items found in {directory_path}"
        
        # Build output
        output = f"Directory: {directory_path}\n"
        output += f"Pattern: {pattern} | Recursive: {recursive}\n"
        output += "═" * 70 + "\n\n"
        
        # Show directories first
        if dirs:
            output += f"📁 Directories ({len(dirs)}):\n"
            output += "─" * 70 + "\n"
            for d in sorted(dirs):
                relative = d.relative_to(path)
                output += f"  {relative}/\n"
            output += "\n"
        
        # Categorize and show files
        if categorize:
            # Group by category
            categorized = {}
            for f in files:
                cat = get_file_category(str(f))
                if cat not in categorized:
                    categorized[cat] = []
                categorized[cat].append(f)
            
            # Display by category
            total_size = 0
            for category in sorted(categorized.keys()):
                files_in_cat = categorized[category]
                cat_size = sum(f.stat().st_size for f in files_in_cat)
                total_size += cat_size
                
                output += f"📄 {category.upper()} ({len(files_in_cat)} files"
                if show_size:
                    output += f", {format_file_size(cat_size)}"
                output += "):\n"
                output += "─" * 70 + "\n"
                
                for f in sorted(files_in_cat):
                    relative = f.relative_to(path)
                    output += f"  {relative}"
                    if show_size:
                        size = f.stat().st_size
                        output += f" ({format_file_size(size)})"
                    output += "\n"
                output += "\n"
            
            # Summary
            output += "═" * 70 + "\n"
            output += f"Summary: {len(files)} files, {len(dirs)} directories"
            if show_size:
                output += f", {format_file_size(total_size)} total"
            output += "\n"
        else:
            # Simple listing
            output += f"📄 Files ({len(files)}):\n"
            output += "─" * 70 + "\n"
            total_size = 0
            for f in sorted(files):
                relative = f.relative_to(path)
                size = f.stat().st_size
                total_size += size
                output += f"  {relative}"
                if show_size:
                    output += f" ({format_file_size(size)})"
                output += "\n"
            
            output += "\n═" * 70 + "\n"
            output += f"Summary: {len(files)} files"
            if show_size:
                output += f", {format_file_size(total_size)} total"
            output += "\n"
        
        return output
        
    except Exception as e:
        return f"✗ Error listing directory {directory_path}: {str(e)}"


@tool("Copy file or directory")
def copy_item(source: str, destination: str, overwrite: bool = False) -> str:
    """
    Copies a file or directory to a new location.
    
    Args:
        source: Source file or directory path
        destination: Destination path
        overwrite: Overwrite if destination exists (default: False)
    
    Returns:
        Success message or error message
    """
    try:
        src = Path(source)
        dst = Path(destination)
        
        if not src.exists():
            return f"✗ Error: Source does not exist: {source}"
        
        if dst.exists() and not overwrite:
            return f"✗ Error: Destination already exists: {destination}\nUse overwrite=True to replace."
        
        # Create parent directory
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        if src.is_file():
            shutil.copy2(src, dst)
            size = dst.stat().st_size
            return f"✓ Successfully copied file: {source} → {destination}\n  Size: {format_file_size(size)}"
        else:
            shutil.copytree(src, dst, dirs_exist_ok=overwrite)
            # Count files
            file_count = sum(1 for _ in dst.rglob('*') if _.is_file())
            return f"✓ Successfully copied directory: {source} → {destination}\n  Files: {file_count}"
        
    except Exception as e:
        return f"✗ Error copying {source}: {str(e)}"


@tool("Move or rename file/directory")
def move_item(source: str, destination: str, overwrite: bool = False) -> str:
    """
    Moves or renames a file or directory.
    
    Args:
        source: Source file or directory path
        destination: Destination path
        overwrite: Overwrite if destination exists (default: False)
    
    Returns:
        Success message or error message
    """
    try:
        src = Path(source)
        dst = Path(destination)
        
        if not src.exists():
            return f"✗ Error: Source does not exist: {source}"
        
        if dst.exists() and not overwrite:
            return f"✗ Error: Destination already exists: {destination}\nUse overwrite=True to replace."
        
        # Create parent directory
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        # Remove destination if overwrite
        if dst.exists() and overwrite:
            if dst.is_file():
                dst.unlink()
            else:
                shutil.rmtree(dst)
        
        shutil.move(str(src), str(dst))
        
        return f"✓ Successfully moved: {source} → {destination}"
        
    except Exception as e:
        return f"✗ Error moving {source}: {str(e)}"


@tool("Delete file or directory")
def delete_item(path: str, recursive: bool = False, confirm: bool = True) -> str:
    """
    Deletes a file or directory.
    
    Args:
        path: Path to file or directory
        recursive: Delete directories recursively (default: False)
        confirm: Require explicit confirmation for deletion (default: True)
    
    Returns:
        Success message or error message
    
    WARNING: Use with caution. Deleted files cannot be recovered.
    """
    try:
        item = Path(path)
        
        if not item.exists():
            return f"✗ Error: Path does not exist: {path}"
        
        # Safety check
        if confirm:
            return f"⚠ DELETE CONFIRMATION REQUIRED\n" \
                   f"Path: {path}\n" \
                   f"Type: {'Directory' if item.is_dir() else 'File'}\n" \
                   f"To proceed, call delete_item with confirm=False"
        
        if item.is_file():
            size = item.stat().st_size
            item.unlink()
            return f"✓ Successfully deleted file: {path}\n  Size freed: {format_file_size(size)}"
        elif item.is_dir():
            if not recursive:
                return f"✗ Error: {path} is a directory. Use recursive=True to delete directories."
            
            # Count files before deletion
            file_count = sum(1 for _ in item.rglob('*') if _.is_file())
            total_size = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
            
            shutil.rmtree(item)
            return f"✓ Successfully deleted directory: {path}\n" \
                   f"  Files deleted: {file_count}\n" \
                   f"  Space freed: {format_file_size(total_size)}"
        
    except Exception as e:
        return f"✗ Error deleting {path}: {str(e)}"


@tool("Get file information")
def get_file_info(file_path: str, detailed: bool = True) -> str:
    """
    Gets detailed information about a file.
    
    Args:
        file_path: Path to the file
        detailed: Show detailed information (default: True)
    
    Returns:
        File information or error message
    """
    try:
        path = Path(file_path)
        
        if not path.exists():
            return f"✗ Error: File does not exist: {file_path}"
        
        stat = path.stat()
        
        output = f"File Information: {file_path}\n"
        output += "═" * 70 + "\n"
        
        # Basic info
        output += f"Type: {'Directory' if path.is_dir() else 'File'}\n"
        output += f"Size: {format_file_size(stat.st_size)}\n"
        
        if path.is_file():
            output += f"Category: {get_file_category(file_path)}\n"
            output += f"Extension: {path.suffix or 'None'}\n"
            
            # Line count for text files
            if not is_binary_file(file_path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        line_count = len(f.readlines())
                    output += f"Lines: {line_count}\n"
                except:
                    pass
        
        if detailed:
            output += f"\n📅 Timestamps:\n"
            output += f"  Created: {datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')}\n"
            output += f"  Modified: {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}\n"
            output += f"  Accessed: {datetime.fromtimestamp(stat.st_atime).strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            output += f"\n🔒 Permissions:\n"
            output += f"  Readable: {os.access(path, os.R_OK)}\n"
            output += f"  Writable: {os.access(path, os.W_OK)}\n"
            output += f"  Executable: {os.access(path, os.X_OK)}\n"
            
            output += f"\n📊 Additional:\n"
            output += f"  Absolute path: {path.absolute()}\n"
            output += f"  Parent: {path.parent}\n"
            output += f"  Is symlink: {path.is_symlink()}\n"
        
        return output
        
    except Exception as e:
        return f"✗ Error getting file info for {file_path}: {str(e)}"


@tool("Search for files")
def search_files(directory: str = ".", pattern: str = "*", content: Optional[str] = None,
                 case_sensitive: bool = False, max_results: int = 100) -> str:
    """
    Searches for files by name pattern or content.
    
    Args:
        directory: Directory to search in (default: current directory)
        pattern: Filename pattern (e.g., '*.py', 'test_*') (default: '*')
        content: Search for this text in file contents (optional)
        case_sensitive: Case-sensitive search (default: False)
        max_results: Maximum number of results to return (default: 100)
    
    Returns:
        Search results with file paths and matches or error message
    """
    try:
        path = Path(directory)
        
        if not path.exists():
            return f"✗ Error: Directory does not exist: {directory}"
        
        # Search by filename
        matches = []
        for item in path.rglob(pattern):
            if item.is_file():
                # Filter hidden files
                if not any(part.startswith('.') for part in item.parts):
                    matches.append(item)
        
        # Filter by content if specified
        if content:
            content_matches = []
            search_term = content if case_sensitive else content.lower()
            
            for file in matches[:max_results]:
                if is_binary_file(str(file)):
                    continue
                
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                        if not case_sensitive:
                            file_content = file_content.lower()
                        
                        if search_term in file_content:
                            # Find line numbers
                            lines = file_content.splitlines()
                            matching_lines = [
                                (i + 1, line.strip()) 
                                for i, line in enumerate(lines) 
                                if search_term in (line if case_sensitive else line.lower())
                            ]
                            content_matches.append((file, matching_lines))
                except:
                    continue
            
            # Format output for content search
            if not content_matches:
                return f"No files found containing '{content}' in {directory}"
            
            output = f"Content Search Results: '{content}'\n"
            output += f"Directory: {directory} | Pattern: {pattern}\n"
            output += f"Found {len(content_matches)} files\n"
            output += "═" * 70 + "\n\n"
            
            for file, matching_lines in content_matches[:max_results]:
                relative = file.relative_to(path)
                output += f"📄 {relative} ({len(matching_lines)} matches)\n"
                for line_no, line in matching_lines[:5]:  # Show first 5 matches per file
                    output += f"  Line {line_no}: {line[:70]}...\n" if len(line) > 70 else f"  Line {line_no}: {line}\n"
                if len(matching_lines) > 5:
                    output += f"  ... and {len(matching_lines) - 5} more matches\n"
                output += "\n"
            
            if len(content_matches) > max_results:
                output += f"... and {len(content_matches) - max_results} more files\n"
            
            return output
        
        # Format output for filename search
        if not matches:
            return f"No files found matching '{pattern}' in {directory}"
        
        output = f"File Search Results: '{pattern}'\n"
        output += f"Directory: {directory}\n"
        output += f"Found {len(matches)} files\n"
        output += "═" * 70 + "\n\n"
        
        total_size = 0
        for file in matches[:max_results]:
            relative = file.relative_to(path)
            size = file.stat().st_size
            total_size += size
            category = get_file_category(str(file))
            output += f"📄 {relative} ({format_file_size(size)}, {category})\n"
        
        if len(matches) > max_results:
            output += f"\n... and {len(matches) - max_results} more files\n"
        
        output += f"\nTotal size: {format_file_size(total_size)}\n"
        
        return output
        
    except Exception as e:
        return f"✗ Error searching files: {str(e)}"


@tool("Create file from template")
def create_from_template(template_path: str, output_path: str, 
                        replacements: Dict[str, str] = None) -> str:
    """
    Creates a new file from a template with variable replacement.
    
    Args:
        template_path: Path to template file
        output_path: Path for output file
        replacements: Dictionary of placeholder:value pairs to replace in template
    
    Returns:
        Success message or error message
    
    Example:
        replacements = {"{{PROJECT_NAME}}": "MyApp", "{{AUTHOR}}": "John Doe"}
    """
    try:
        # Read template
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Apply replacements
        if replacements:
            for placeholder, value in replacements.items():
                content = content.replace(placeholder, value)
        
        # Write output
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output, 'w', encoding='utf-8') as f:
            f.write(content)
        
        size = output.stat().st_size
        return f"✓ Successfully created file from template\n" \
               f"  Template: {template_path}\n" \
               f"  Output: {output_path}\n" \
               f"  Size: {format_file_size(size)}\n" \
               f"  Replacements: {len(replacements) if replacements else 0}"
        
    except Exception as e:
        return f"✗ Error creating file from template: {str(e)}"