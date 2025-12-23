import os
import time
from typing import List

from autofill.actions.base import BaseAction
from autofill.models import FillCommand, FillResult, ActionType
from autofill.exceptions import ElementNotFoundError, ActionExecutionError


class UploadFileAction(BaseAction):
    action_type = ActionType.UPLOAD_FILE
    
    def execute(self, command: FillCommand) -> FillResult:
        start = time.time()
        
        try:
            file_paths = self._get_file_paths(command)
            
            if not file_paths:
                duration = int((time.time() - start) * 1000)
                return self._create_result(
                    command,
                    success=False,
                    error="No file path provided",
                    duration_ms=duration,
                )
            
            # Validate all files exist
            for path in file_paths:
                if not os.path.exists(path):
                    duration = int((time.time() - start) * 1000)
                    # Show original and resolved path for debugging
                    original = command.file_path or (command.file_paths[0] if command.file_paths else command.value)
                    return self._create_result(
                        command,
                        success=False,
                        error=f"File not found: {path} (original: {original})",
                        duration_ms=duration,
                    )
            
            element = self.locator.find(
                command.selector,
                command.selector_type,
                command.timeout_ms,
            )
            
            # Log the absolute path being used
            print(f"  [UPLOAD] Uploading file(s): {file_paths}")
            
            if len(file_paths) == 1:
                element.send_keys(file_paths[0])
            else:
                element.send_keys("\n".join(file_paths))
            
            self._wait_after(command)
            
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=True,
                value_used=file_paths if len(file_paths) > 1 else file_paths[0],
                duration_ms=duration,
            )
            
        except ElementNotFoundError:
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=False,
                element_found=False,
                error=f"File input not found: {command.selector}",
                duration_ms=duration,
            )
        except Exception as e:
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=False,
                error=str(e),
                duration_ms=duration,
            )
    
    def _get_file_paths(self, command: FillCommand) -> List[str]:
        """Get file paths from command, converting relative paths to absolute."""
        raw_paths = []
        
        if command.file_paths:
            raw_paths = command.file_paths
        elif command.file_path:
            raw_paths = [command.file_path]
        elif command.value:
            if isinstance(command.value, list):
                raw_paths = command.value
            else:
                raw_paths = [str(command.value)]
        
        if not raw_paths:
            return []
        
        # Convert all paths to absolute paths (required by Selenium)
        absolute_paths = []
        for path in raw_paths:
            if path:
                # Normalize path separators and convert to absolute
                normalized = os.path.normpath(path)
                if not os.path.isabs(normalized):
                    # Convert relative path to absolute
                    absolute = os.path.abspath(normalized)
                else:
                    absolute = normalized
                absolute_paths.append(absolute)
        
        return absolute_paths

