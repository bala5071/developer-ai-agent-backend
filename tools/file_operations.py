import os
import json
import shutil
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Union
from datetime import datetime
from crewai.tools import tool

# ── Supabase integration ──────────────────────────────────────────────────────
# This module-level variable holds the current session ID.
# pipeline.py sets it with set_current_session() before running a crew.
# write_file reads it so it knows which session to save files under.
# If it's None (e.g. running locally without a session), saving is skipped.
_current_session_id: Optional[str] = None


def set_current_session(session_id: str) -> None:
    """
    Called by pipeline.py before running any crew.
    Tells write_file which session to save files to in Supabase.
    """
    global _current_session_id
    _current_session_id = session_id


def get_current_session() -> Optional[str]:
    """Returns the currently active session ID."""
    return _current_session_id


# ─────────────────────────────────────────────────────────────────────────────
# File type categorization (unchanged from your original)
# ─────────────────────────────────────────────────────────────────────────────
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
    path = Path(file_path)
    ext = path.suffix.lower()
    name = path.name
    for lang, extensions in FILE_CATEGORIES['source_code'].items():
        if ext in extensions:
            return f'source_code/{lang}'
    for category, extensions in FILE_CATEGORIES.items():
        if category != 'source_code':
            if ext in extensions or name in extensions:
                return category
    return 'other'


def is_binary_file(file_path: str) -> bool:
    ext = Path(file_path).suffix.lower()
    return ext in BINARY_EXTENSIONS


def format_file_size(size_bytes: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


# ─────────────────────────────────────────────────────────────────────────────
# write_file — MODIFIED to also save to Supabase
# Everything else in this file is unchanged from your original.
# ─────────────────────────────────────────────────────────────────────────────

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

        # Write to disk (same as before)
        with open(path, mode, encoding=encoding) as f:
            f.write(content)

        # ── NEW: also save to Supabase ────────────────────────────────────────
        # Only runs when there's an active session (i.e. called from pipeline.py).
        # If _current_session_id is None (local testing, CLI mode), this is skipped.
        session_id = _current_session_id
        db_saved = False

        if session_id and not is_binary_file(file_path):
            try:
                from backend.database import save_file as db_save_file

                # Store a relative path in the DB if possible,
                # so it's portable when restored to a different machine.
                # Falls back to the full path if we can't make it relative.
                try:
                    from config import OUTPUT_DIR
                    relative_path = str(path.relative_to(OUTPUT_DIR))
                except Exception:
                    relative_path = str(path)

                # For append mode, read the full file content after writing
                # so the DB always has the complete file, not just the appended chunk.
                if mode == 'a':
                    with open(path, 'r', encoding=encoding) as f:
                        full_content = f.read()
                    db_save_file(session_id, relative_path, full_content)
                else:
                    db_save_file(session_id, relative_path, content)

                db_saved = True
            except Exception as db_err:
                # DB save failure should NOT fail the tool —
                # the file is already written to disk, which is what matters for the agent.
                # We just log the warning and continue.
                import logging
                logging.getLogger(__name__).warning(
                    f"Supabase save failed for {file_path}: {db_err}"
                )
        # ── END NEW ───────────────────────────────────────────────────────────

        # Get file info for the return message
        size = path.stat().st_size
        category = get_file_category(file_path)

        result = f"✓ Successfully wrote to: {file_path}\n"
        result += f"  Size: {format_file_size(size)}\n"
        result += f"  Category: {category}\n"
        result += f"  Mode: {'Append' if mode == 'a' else 'Write'}\n"
        result += f"  Lines: {len(content.splitlines())}\n"
        result += f"  Saved to database: {'✓ Yes' if db_saved else '— No (no active session)'}"

        if create_backup:
            result += f"\n  Backup created: {path.with_suffix(path.suffix + '.backup')}"

        return result

    except Exception as e:
        return f"✗ Error writing file {file_path}: {str(e)}"


# ─────────────────────────────────────────────────────────────────────────────
# All remaining tools below are UNCHANGED from your original file_operations.py
# ─────────────────────────────────────────────────────────────────────────────

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
        if is_binary_file(file_path):
            size = path.stat().st_size
            return f"⚠ Binary file detected: {file_path}\nSize: {format_file_size(size)}\nUse binary read operations for this file."
        with open(path, 'r', encoding=encoding) as f:
            lines = f.readlines()
        if start_line > 1:
            lines = lines[start_line - 1:]
        if max_lines:
            lines = lines[:max_lines]
        content = ''.join(lines)
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
    """Appends content to an existing file or creates a new one."""
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
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
    """Creates a directory structure with optional initialization files."""
    try:
        path = Path(directory_path)
        path.mkdir(parents=True, exist_ok=True)
        result = f"✓ Successfully created directory: {directory_path}"
        if with_init:
            parent_has_py = any(path.parent.glob('*.py'))
            if parent_has_py or '__pycache__' in str(directory_path):
                init_file = path / '__init__.py'
                with open(init_file, 'w', encoding='utf-8') as f:
                    f.write(init_content if init_content else '"""Package initialization."""\n')
                result += f"\n  Created: __init__.py"
            else:
                init_file = path / 'index.js'
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
    """Lists files and directories with advanced filtering and organization."""
    try:
        path = Path(directory_path)
        if not path.exists():
            return f"✗ Error: Directory does not exist: {directory_path}"
        if not path.is_dir():
            return f"✗ Error: Not a directory: {directory_path}"
        if recursive:
            items = list(path.rglob(pattern))
        else:
            items = list(path.glob(pattern))
        if not show_hidden:
            items = [item for item in items if not any(part.startswith('.') for part in item.parts)]
        files = [item for item in items if item.is_file()]
        dirs = [item for item in items if item.is_dir()]
        if not files and not dirs:
            return f"No items found in {directory_path}"
        output = f"Directory: {directory_path}\nPattern: {pattern} | Recursive: {recursive}\n{'═' * 70}\n\n"
        if dirs:
            output += f"📁 Directories ({len(dirs)}):\n{'─' * 70}\n"
            for d in sorted(dirs):
                output += f"  {d.relative_to(path)}/\n"
            output += "\n"
        if categorize:
            categorized = {}
            for f in files:
                cat = get_file_category(str(f))
                categorized.setdefault(cat, []).append(f)
            total_size = 0
            for category in sorted(categorized.keys()):
                files_in_cat = categorized[category]
                cat_size = sum(f.stat().st_size for f in files_in_cat)
                total_size += cat_size
                output += f"📄 {category.upper()} ({len(files_in_cat)} files"
                if show_size:
                    output += f", {format_file_size(cat_size)}"
                output += "):\n" + "─" * 70 + "\n"
                for f in sorted(files_in_cat):
                    output += f"  {f.relative_to(path)}"
                    if show_size:
                        output += f" ({format_file_size(f.stat().st_size)})"
                    output += "\n"
                output += "\n"
            output += f"{'═' * 70}\nSummary: {len(files)} files, {len(dirs)} directories"
            if show_size:
                output += f", {format_file_size(total_size)} total"
            output += "\n"
        else:
            output += f"📄 Files ({len(files)}):\n{'─' * 70}\n"
            total_size = 0
            for f in sorted(files):
                size = f.stat().st_size
                total_size += size
                output += f"  {f.relative_to(path)}"
                if show_size:
                    output += f" ({format_file_size(size)})"
                output += "\n"
            output += f"\n{'═' * 70}\nSummary: {len(files)} files"
            if show_size:
                output += f", {format_file_size(total_size)} total"
            output += "\n"
        return output
    except Exception as e:
        return f"✗ Error listing directory {directory_path}: {str(e)}"


@tool("Copy file or directory")
def copy_item(source: str, destination: str, overwrite: bool = False) -> str:
    """Copies a file or directory to a new location."""
    try:
        src, dst = Path(source), Path(destination)
        if not src.exists():
            return f"✗ Error: Source does not exist: {source}"
        if dst.exists() and not overwrite:
            return f"✗ Error: Destination already exists: {destination}\nUse overwrite=True to replace."
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_file():
            shutil.copy2(src, dst)
            return f"✓ Successfully copied file: {source} → {destination}\n  Size: {format_file_size(dst.stat().st_size)}"
        else:
            shutil.copytree(src, dst, dirs_exist_ok=overwrite)
            return f"✓ Successfully copied directory: {source} → {destination}\n  Files: {sum(1 for _ in dst.rglob('*') if _.is_file())}"
    except Exception as e:
        return f"✗ Error copying {source}: {str(e)}"


@tool("Move or rename file/directory")
def move_item(source: str, destination: str, overwrite: bool = False) -> str:
    """Moves or renames a file or directory."""
    try:
        src, dst = Path(source), Path(destination)
        if not src.exists():
            return f"✗ Error: Source does not exist: {source}"
        if dst.exists() and not overwrite:
            return f"✗ Error: Destination already exists: {destination}\nUse overwrite=True to replace."
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and overwrite:
            dst.unlink() if dst.is_file() else shutil.rmtree(dst)
        shutil.move(str(src), str(dst))
        return f"✓ Successfully moved: {source} → {destination}"
    except Exception as e:
        return f"✗ Error moving {source}: {str(e)}"


@tool("Delete file or directory")
def delete_item(path: str, recursive: bool = False, confirm: bool = True) -> str:
    """Deletes a file or directory."""
    try:
        item = Path(path)
        if not item.exists():
            return f"✗ Error: Path does not exist: {path}"
        if confirm:
            return (f"⚠ DELETE CONFIRMATION REQUIRED\nPath: {path}\n"
                    f"Type: {'Directory' if item.is_dir() else 'File'}\n"
                    f"To proceed, call delete_item with confirm=False")
        if item.is_file():
            size = item.stat().st_size
            item.unlink()
            return f"✓ Successfully deleted file: {path}\n  Size freed: {format_file_size(size)}"
        elif item.is_dir():
            if not recursive:
                return f"✗ Error: {path} is a directory. Use recursive=True to delete directories."
            file_count = sum(1 for _ in item.rglob('*') if _.is_file())
            total_size = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
            shutil.rmtree(item)
            return (f"✓ Successfully deleted directory: {path}\n"
                    f"  Files deleted: {file_count}\n"
                    f"  Space freed: {format_file_size(total_size)}")
    except Exception as e:
        return f"✗ Error deleting {path}: {str(e)}"


@tool("Get file information")
def get_file_info(file_path: str, detailed: bool = True) -> str:
    """Gets detailed information about a file."""
    try:
        path = Path(file_path)
        if not path.exists():
            return f"✗ Error: File does not exist: {file_path}"
        stat = path.stat()
        output = f"File Information: {file_path}\n{'═' * 70}\n"
        output += f"Type: {'Directory' if path.is_dir() else 'File'}\nSize: {format_file_size(stat.st_size)}\n"
        if path.is_file():
            output += f"Category: {get_file_category(file_path)}\nExtension: {path.suffix or 'None'}\n"
            if not is_binary_file(file_path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        output += f"Lines: {len(f.readlines())}\n"
                except Exception:
                    pass
        if detailed:
            output += (f"\n📅 Timestamps:\n"
                       f"  Modified: {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}\n"
                       f"\n📊 Additional:\n"
                       f"  Absolute path: {path.absolute()}\n"
                       f"  Parent: {path.parent}\n")
        return output
    except Exception as e:
        return f"✗ Error getting file info for {file_path}: {str(e)}"


@tool("Search for files")
def search_files(directory: str = ".", pattern: str = "*", content: Optional[str] = None,
                 case_sensitive: bool = False, max_results: int = 100) -> str:
    """Searches for files by name pattern or content."""
    try:
        path = Path(directory)
        if not path.exists():
            return f"✗ Error: Directory does not exist: {directory}"
        matches = [item for item in path.rglob(pattern)
                   if item.is_file() and not any(p.startswith('.') for p in item.parts)]
        if content:
            search_term = content if case_sensitive else content.lower()
            content_matches = []
            for file in matches[:max_results]:
                if is_binary_file(str(file)):
                    continue
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    fc = file_content if case_sensitive else file_content.lower()
                    if search_term in fc:
                        lines = fc.splitlines()
                        matching = [(i + 1, l.strip()) for i, l in enumerate(lines) if search_term in l]
                        content_matches.append((file, matching))
                except Exception:
                    continue
            if not content_matches:
                return f"No files found containing '{content}' in {directory}"
            output = f"Content Search Results: '{content}'\nFound {len(content_matches)} files\n{'═' * 70}\n\n"
            for file, matching_lines in content_matches[:max_results]:
                output += f"📄 {file.relative_to(path)} ({len(matching_lines)} matches)\n"
                for line_no, line in matching_lines[:5]:
                    output += f"  Line {line_no}: {line[:70]}\n"
                output += "\n"
            return output
        if not matches:
            return f"No files found matching '{pattern}' in {directory}"
        output = f"File Search Results: '{pattern}'\nFound {len(matches)} files\n{'═' * 70}\n\n"
        total_size = 0
        for file in matches[:max_results]:
            size = file.stat().st_size
            total_size += size
            output += f"📄 {file.relative_to(path)} ({format_file_size(size)}, {get_file_category(str(file))})\n"
        output += f"\nTotal size: {format_file_size(total_size)}\n"
        return output
    except Exception as e:
        return f"✗ Error searching files: {str(e)}"


@tool("Create file from template")
def create_from_template(template_path: str, output_path: str,
                         replacements: Dict[str, str] = None) -> str:
    """Creates a new file from a template with variable replacement."""
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if replacements:
            for placeholder, value in replacements.items():
                content = content.replace(placeholder, value)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, 'w', encoding='utf-8') as f:
            f.write(content)
        size = output.stat().st_size
        return (f"✓ Successfully created file from template\n"
                f"  Template: {template_path}\n"
                f"  Output: {output_path}\n"
                f"  Size: {format_file_size(size)}\n"
                f"  Replacements: {len(replacements) if replacements else 0}")
    except Exception as e:
        return f"✗ Error creating file from template: {str(e)}"