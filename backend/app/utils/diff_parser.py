import re
from typing import List, Dict, Any

class DiffParser:
    """Parses Git diff strings into structured Python dictionary format."""

    @staticmethod
    def parse_diff(raw_diff: str) -> List[Dict[str, Any]]:
        files = []
        if not raw_diff:
            return files

        # Split diff by file header
        file_chunks = re.split(r'^diff --git ', raw_diff, flags=re.MULTILINE)

        for chunk in file_chunks:
            if not chunk.strip():
                continue

            lines = chunk.split('\n')
            header_line = lines[0]
            
            # Extract file paths
            match = re.search(r'a/(.*?)\s+b/(.*)', header_line)
            if match:
                old_path, new_path = match.group(1), match.group(2)
            else:
                new_path = "unknown"
                old_path = "unknown"

            added_lines = []
            removed_lines = []
            hunks = []
            
            current_line_new = 0
            current_line_old = 0
            
            for line in lines[1:]:
                if line.startswith('@@'):
                    # Hunk header e.g. @@ -10,5 +10,8 @@
                    hunk_match = re.search(r'@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@', line)
                    if hunk_match:
                        current_line_old = int(hunk_match.group(1))
                        current_line_new = int(hunk_match.group(2))
                    hunks.append(line)
                elif line.startswith('+') and not line.startswith('+++'):
                    added_lines.append({
                        'line_number': current_line_new,
                        'content': line[1:]
                    })
                    current_line_new += 1
                elif line.startswith('-') and not line.startswith('---'):
                    removed_lines.append({
                        'line_number': current_line_old,
                        'content': line[1:]
                    })
                    current_line_old += 1
                elif line.startswith(' '):
                    current_line_new += 1
                    current_line_old += 1

            files.append({
                'filename': new_path,
                'old_path': old_path,
                'additions': len(added_lines),
                'deletions': len(removed_lines),
                'added_lines': added_lines,
                'removed_lines': removed_lines,
                'hunks': hunks,
                'full_chunk': chunk
            })

        return files
