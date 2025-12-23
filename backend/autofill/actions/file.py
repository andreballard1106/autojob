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
            
            for path in file_paths:
                if not os.path.exists(path):
                    duration = int((time.time() - start) * 1000)
                    return self._create_result(
                        command,
                        success=False,
                        error=f"File not found: {path}",
                        duration_ms=duration,
                    )
            
            element = self.locator.find(
                command.selector,
                command.selector_type,
                command.timeout_ms,
            )
            
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
        if command.file_paths:
            return command.file_paths
        elif command.file_path:
            return [command.file_path]
        elif command.value:
            if isinstance(command.value, list):
                return command.value
            return [str(command.value)]
        return []

