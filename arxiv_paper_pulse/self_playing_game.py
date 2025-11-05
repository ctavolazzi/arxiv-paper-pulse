# arxiv_paper_pulse/self_playing_game.py
from google import genai
from pathlib import Path
import json
import time
import subprocess
import tempfile
import sys
import ast
import re
from datetime import datetime
from . import config


class SelfDesigningGame:
    """
    Standalone game generation module using Gemini API.
    Modular component that can be used independently or composed with other systems.

    Games are saved to: arxiv_paper_pulse/data/self_generated_games/
    """

    def __init__(self, api_key=None, model=None, output_dir=None):
        self.api_key = api_key or config.GEMINI_API_KEY
        self.model = model or "gemini-2.5-flash"
        self.output_dir = Path(output_dir or config.GAME_OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.client = genai.Client(api_key=self.api_key)

    def extract_python_code(self, text: str) -> str:
        """
        Extract Python code from markdown code blocks.

        Args:
            text: Text that may contain markdown code blocks

        Returns:
            Extracted Python code string
        """
        # Find all code blocks (with or without python tag)
        pattern = r'```(?:python)?\s*(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)

        if not matches:
            # No code blocks, assume entire text is code
            return text.strip()

        # Return longest match (likely the actual code)
        return max(matches, key=len).strip()

    def validate_game_structure(self, code: str) -> tuple[bool, str]:
        """
        Validate code has Game class with play() method.

        Args:
            code: Python code to validate

        Returns:
            (is_valid: bool, error_message: str)
        """
        try:
            tree = ast.parse(code)

            # Find Game class
            game_class = None
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == 'Game':
                    game_class = node
                    break

            if not game_class:
                return False, "No 'Game' class found"

            # Check for play method
            method_names = [item.name for item in game_class.body
                          if isinstance(item, ast.FunctionDef)]

            if 'play' not in method_names:
                return False, "No 'play()' method found in Game class"

            return True, "Valid structure"

        except SyntaxError as e:
            return False, f"Syntax error: {e.msg} at line {e.lineno}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def design_game(self, prompt: str) -> dict:
        """
        Generate game code using Gemini API.

        Args:
            prompt: Game description prompt

        Returns:
            Dict with 'code', 'valid', 'error', 'raw_response', 'response_time'
        """
        start_time = time.time()

        # Game generation prompt with explicit constraints
        game_prompt = f"""Generate a Python simulation game. Requirements:
{prompt}

CONSTRAINTS:
- Must be a deterministic simulation (no random numbers, no user input)
- Must define a Game class with __init__() and play() methods
- play() should run the simulation and print state using print()
- NO input() calls allowed
- Keep it simple and complete (50-200 lines max)
- Use only Python standard library

RETURN FORMAT:
Return ONLY Python code in a markdown code block like this:
```python
class Game:
    def __init__(self):
        # Initialize simulation
        pass

    def play(self):
        # Run simulation and print state
        pass
```

Make sure the code is complete, valid Python that can run."""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[game_prompt]
            )

            response_time = time.time() - start_time
            raw_response = response.text

            # Extract code from response
            code = self.extract_python_code(raw_response)

            # Validate structure
            is_valid, error_msg = self.validate_game_structure(code)

            return {
                'code': code,
                'valid': is_valid,
                'error': error_msg,
                'raw_response': raw_response,
                'response_time': response_time
            }

        except Exception as e:
            return {
                'code': '',
                'valid': False,
                'error': f"API error: {str(e)}",
                'raw_response': '',
                'response_time': time.time() - start_time
            }

    def execute_game(self, code: str, timeout: int = 30) -> dict:
        """
        Execute generated game code in isolated subprocess.

        Args:
            code: Python code to execute
            timeout: Maximum execution time in seconds

        Returns:
            Dict with 'success', 'stdout', 'stderr', 'returncode', 'execution_time'
        """
        start_time = time.time()

        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name

        try:
            # Execute in subprocess with timeout
            result = subprocess.run(
                [sys.executable, temp_path],
                capture_output=True,
                timeout=timeout,
                text=True,
                env={'PYTHONPATH': ''},  # Minimal environment
                cwd=None
            )

            execution_time = time.time() - start_time

            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode,
                'execution_time': execution_time
            }

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            return {
                'success': False,
                'stdout': '',
                'stderr': f'Execution timeout after {timeout} seconds',
                'returncode': -1,
                'execution_time': execution_time
            }
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                'success': False,
                'stdout': '',
                'stderr': f'Execution error: {str(e)}',
                'returncode': -1,
                'execution_time': execution_time
            }
        finally:
            # Always cleanup temp file
            try:
                import os
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except:
                pass

    def save_game(self, code: str, execution_result: dict, game_dir: Path = None) -> Path:
        """
        Save game code and execution results to directory.

        Args:
            code: Generated Python code
            execution_result: Execution result dict
            game_dir: Optional directory path (defaults to self.output_dir)

        Returns:
            Path to saved game directory
        """
        if game_dir is None:
            game_dir = self.output_dir

        # Create timestamped directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Get next game number
        existing_games = list(game_dir.glob("game_*"))
        game_number = len(existing_games) + 1

        save_dir = game_dir / f"game_{game_number:03d}_{timestamp}"
        save_dir.mkdir(parents=True, exist_ok=True)

        # Save code
        code_path = save_dir / "game.py"
        code_path.write_text(code, encoding='utf-8')

        # Save execution results
        results_path = save_dir / "execution_results.json"
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(execution_result, f, indent=2, ensure_ascii=False)

        return save_dir

