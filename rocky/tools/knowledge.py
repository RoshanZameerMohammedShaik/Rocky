"""Knowledge base tool for Rocky.AI using simple file-based storage."""

import json
import hashlib
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from rocky.tools.base import Tool, ToolResult, ToolParameter
from rocky.config import get_config
from rocky.utils.logging import get_logger
from rocky.utils.validators import is_binary_file

logger = get_logger(__name__)


@dataclass
class KnowledgeEntry:
    """A knowledge base entry."""
    id: str
    path: str
    content: str
    chunk_index: int
    total_chunks: int


class SimpleKnowledgeBase:
    """Simple file-based knowledge base with keyword search."""
    
    def __init__(self, storage_path: Optional[Path] = None):
        config = get_config()
        self.storage_path = storage_path or config.paths.knowledge
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.index_file = self.storage_path / "index.json"
        self._index: dict = self._load_index()
    
    def _load_index(self) -> dict:
        """Load the index from disk."""
        if self.index_file.exists():
            try:
                with open(self.index_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load index: {e}")
        return {"entries": {}, "files": {}}
    
    def _save_index(self):
        """Save the index to disk."""
        with open(self.index_file, "w") as f:
            json.dump(self._index, f, indent=2)
    
    def _chunk_text(self, text: str, chunk_size: int = 1000) -> list[str]:
        """Split text into chunks."""
        chunks = []
        lines = text.splitlines()
        current_chunk = []
        current_size = 0
        
        for line in lines:
            line_size = len(line) + 1
            if current_size + line_size > chunk_size and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_size = 0
            current_chunk.append(line)
            current_size += line_size
        
        if current_chunk:
            chunks.append("\n".join(current_chunk))
        
        return chunks
    
    def _generate_id(self, path: str, chunk_index: int) -> str:
        """Generate a unique ID for a chunk."""
        content = f"{path}:{chunk_index}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def index_file_path(self, file_path: Path) -> int:
        """Index a single file. Returns number of chunks indexed."""
        if not file_path.exists():
            return 0
        
        if is_binary_file(file_path):
            return 0
        
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return 0
        
        chunks = self._chunk_text(content)
        str_path = str(file_path.resolve())
        
        # Remove old entries for this file
        self._remove_file_entries(str_path)
        
        # Add new entries
        chunk_ids = []
        for i, chunk in enumerate(chunks):
            chunk_id = self._generate_id(str_path, i)
            self._index["entries"][chunk_id] = {
                "path": str_path,
                "content": chunk,
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            chunk_ids.append(chunk_id)
        
        self._index["files"][str_path] = chunk_ids
        self._save_index()
        
        return len(chunks)
    
    def index_directory(self, dir_path: Path, pattern: str = "*") -> int:
        """Index all files in a directory. Returns total chunks indexed."""
        total = 0
        for file_path in dir_path.rglob(pattern):
            if file_path.is_file():
                total += self.index_file_path(file_path)
        return total
    
    def _remove_file_entries(self, file_path: str):
        """Remove all entries for a file."""
        if file_path in self._index["files"]:
            for chunk_id in self._index["files"][file_path]:
                self._index["entries"].pop(chunk_id, None)
            del self._index["files"][file_path]
    
    def search(self, query: str, max_results: int = 5) -> list[KnowledgeEntry]:
        """Search the knowledge base using keyword matching."""
        query_lower = query.lower()
        query_terms = query_lower.split()
        
        results = []
        
        for chunk_id, entry in self._index["entries"].items():
            content_lower = entry["content"].lower()
            
            # Score based on term matches
            score = sum(1 for term in query_terms if term in content_lower)
            
            if score > 0:
                results.append((score, KnowledgeEntry(
                    id=chunk_id,
                    path=entry["path"],
                    content=entry["content"],
                    chunk_index=entry["chunk_index"],
                    total_chunks=entry["total_chunks"],
                )))
        
        # Sort by score descending
        results.sort(key=lambda x: x[0], reverse=True)
        
        return [entry for _, entry in results[:max_results]]
    
    def get_stats(self) -> dict:
        """Get knowledge base statistics."""
        return {
            "files": len(self._index["files"]),
            "chunks": len(self._index["entries"]),
        }
    
    def clear(self):
        """Clear the knowledge base."""
        self._index = {"entries": {}, "files": {}}
        self._save_index()


class IndexFilesTool(Tool):
    """Index files into the knowledge base."""
    
    def __init__(self):
        super().__init__(
            name="index_files",
            description="Index files or directories into the knowledge base for later search.",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to file or directory to index",
                    required=True
                ),
                ToolParameter(
                    name="pattern",
                    type="string",
                    description="File pattern for directory indexing (e.g., '*.py')",
                    required=False,
                    default="*"
                ),
            ]
        )
        self.kb = SimpleKnowledgeBase()
    
    def execute(self, path: str, pattern: str = "*") -> ToolResult:
        target = Path(path).expanduser().resolve()
        
        if not target.exists():
            return ToolResult.fail(f"Path not found: {path}")
        
        try:
            if target.is_file():
                chunks = self.kb.index_file_path(target)
                return ToolResult.ok(
                    f"Indexed {target.name}: {chunks} chunks",
                    data={"path": str(target), "chunks": chunks}
                )
            else:
                chunks = self.kb.index_directory(target, pattern)
                stats = self.kb.get_stats()
                return ToolResult.ok(
                    f"Indexed directory: {chunks} chunks from {stats['files']} files",
                    data={"path": str(target), "chunks": chunks, "files": stats["files"]}
                )
                
        except Exception as e:
            logger.error(f"Indexing error: {e}")
            return ToolResult.fail(f"Failed to index: {e}")


class SearchKnowledgeTool(Tool):
    """Search the knowledge base."""
    
    def __init__(self):
        super().__init__(
            name="search_knowledge",
            description="Search the indexed knowledge base for relevant information.",
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query",
                    required=True
                ),
                ToolParameter(
                    name="max_results",
                    type="integer",
                    description="Maximum number of results",
                    required=False,
                    default=5
                ),
            ]
        )
        self.kb = SimpleKnowledgeBase()
    
    def execute(self, query: str, max_results: int = 5) -> ToolResult:
        try:
            results = self.kb.search(query, max_results)
            
            if not results:
                stats = self.kb.get_stats()
                if stats["chunks"] == 0:
                    return ToolResult.ok(
                        "Knowledge base is empty. Use index_files to add content.",
                        data={"results": []}
                    )
                return ToolResult.ok(
                    f"No results found for: {query}",
                    data={"results": []}
                )
            
            output_lines = [f"Found {len(results)} results for: {query}\n"]
            
            for i, entry in enumerate(results, 1):
                file_name = Path(entry.path).name
                preview = entry.content[:200].replace("\n", " ")
                output_lines.append(f"{i}. {file_name} (chunk {entry.chunk_index + 1}/{entry.total_chunks})")
                output_lines.append(f"   {preview}...")
                output_lines.append("")
            
            return ToolResult.ok(
                "\n".join(output_lines),
                data={"results": [{"path": e.path, "content": e.content} for e in results]}
            )
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return ToolResult.fail(f"Search failed: {e}")
