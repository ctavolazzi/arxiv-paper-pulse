# tests/test_self_playing_game.py

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import subprocess
import ast

from arxiv_paper_pulse.self_playing_game import SelfDesigningGame


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini client for game generation testing"""
    with patch('arxiv_paper_pulse.self_playing_game.genai.Client') as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock response with game code
        mock_response = Mock()
        mock_response.text = """```python
class Game:
    def __init__(self):
        self.grid = [[0, 1, 0], [1, 0, 1], [0, 1, 0]]

    def play(self):
        for row in self.grid:
            print(' '.join(str(cell) for cell in row))
```
"""
        mock_client.models.generate_content.return_value = mock_response

        yield mock_client


@pytest.fixture
def temp_game_dir(tmp_path):
    """Temporary directory for game output"""
    game_dir = tmp_path / "self_generated_games"
    game_dir.mkdir(parents=True, exist_ok=True)
    return game_dir


@pytest.fixture
def game_generator(mock_gemini_client, temp_game_dir, monkeypatch):
    """Create SelfDesigningGame instance with mocked client and temp directory"""
    monkeypatch.setattr('arxiv_paper_pulse.config.GAME_OUTPUT_DIR', str(temp_game_dir))
    monkeypatch.setattr('arxiv_paper_pulse.config.GEMINI_API_KEY', 'test_key')

    generator = SelfDesigningGame(output_dir=str(temp_game_dir))
    generator.client = mock_gemini_client
    return generator


class TestCodeExtraction:
    """Tests for code extraction from markdown"""

    def test_extract_from_markdown_block(self, game_generator):
        """Test extraction from markdown code block"""
        text = """Here's some explanation.
```python
class Game:
    def play(self):
        print("Hello")
```
More explanation."""

        code = game_generator.extract_python_code(text)
        assert 'class Game' in code
        assert 'def play(self):' in code
        assert 'print("Hello")' in code

    def test_extract_without_markdown(self, game_generator):
        """Test extraction when no markdown blocks exist"""
        text = """class Game:
    def play(self):
        print("Hello")"""

        code = game_generator.extract_python_code(text)
        assert code.strip() == text.strip()

    def test_extract_multiple_blocks_takes_longest(self, game_generator):
        """Test that longest code block is selected when multiple exist"""
        text = """Short code:
```python
x = 1
```
Long code:
```python
class Game:
    def __init__(self):
        self.value = 42

    def play(self):
        for i in range(10):
            print(i)
```
"""
        code = game_generator.extract_python_code(text)
        assert 'class Game' in code
        assert 'for i in range(10)' in code
        assert 'x = 1' not in code or 'x = 1' not in code[:50]  # Longest should be selected


class TestStructureValidation:
    """Tests for game structure validation"""

    def test_valid_game_structure(self, game_generator):
        """Test validation of valid game structure"""
        code = """class Game:
    def __init__(self):
        pass

    def play(self):
        print("Playing")
"""
        is_valid, error = game_generator.validate_game_structure(code)
        assert is_valid is True
        assert error == "Valid structure"

    def test_missing_game_class(self, game_generator):
        """Test validation fails when Game class is missing"""
        code = """def play():
    print("Hello")
"""
        is_valid, error = game_generator.validate_game_structure(code)
        assert is_valid is False
        assert "No 'Game' class found" in error

    def test_missing_play_method(self, game_generator):
        """Test validation fails when play() method is missing"""
        code = """class Game:
    def __init__(self):
        pass
"""
        is_valid, error = game_generator.validate_game_structure(code)
        assert is_valid is False
        assert "No 'play()' method found" in error

    def test_syntax_error_handling(self, game_generator):
        """Test validation handles syntax errors"""
        code = """class Game:
    def play(self):
        print("unclosed string
"""
        is_valid, error = game_generator.validate_game_structure(code)
        assert is_valid is False
        assert "Syntax error" in error


class TestGameExecution:
    """Tests for game code execution"""

    def test_execute_valid_code(self, game_generator):
        """Test execution of valid game code"""
        code = """class Game:
    def __init__(self):
        self.value = 42

    def play(self):
        print("Game output")
        print(f"Value: {self.value}")

if __name__ == "__main__":
    game = Game()
    game.play()
"""
        result = game_generator.execute_game(code, timeout=5)

        assert result['success'] is True
        assert result['returncode'] == 0
        assert 'Game output' in result['stdout']
        assert 'Value: 42' in result['stdout']

    def test_execute_syntax_error(self, game_generator):
        """Test execution fails on syntax error"""
        code = """class Game:
    def play(self):
        print("unclosed string
"""
        result = game_generator.execute_game(code, timeout=5)

        assert result['success'] is False
        assert result['returncode'] != 0
        assert 'SyntaxError' in result['stderr'] or 'error' in result['stderr'].lower()

    def test_execute_timeout(self, game_generator):
        """Test execution times out for infinite loop"""
        code = """class Game:
    def play(self):
        while True:
            pass

if __name__ == "__main__":
    game = Game()
    game.play()
"""
        result = game_generator.execute_game(code, timeout=1)

        assert result['success'] is False
        assert 'timeout' in result['stderr'].lower()


class TestGameDesign:
    """Tests for game design (with mocked API)"""

    def test_design_game_success(self, game_generator):
        """Test successful game design"""
        prompt = "Create a simple grid game"

        result = game_generator.design_game(prompt)

        assert 'code' in result
        assert 'valid' in result
        assert result['valid'] is True
        assert 'class Game' in result['code']

    def test_design_game_invalid_structure(self, game_generator, mock_gemini_client):
        """Test game design with invalid structure"""
        # Mock response with invalid code
        mock_response = Mock()
        mock_response.text = """Here's some code:
```python
def play():
    print("No Game class")
```
"""
        mock_gemini_client.models.generate_content.return_value = mock_response

        result = game_generator.design_game("test prompt")

        assert result['valid'] is False
        assert "No 'Game' class found" in result['error']


class TestGameSaving:
    """Tests for saving games"""

    def test_save_game(self, game_generator, temp_game_dir):
        """Test saving game code and execution results"""
        code = """class Game:
    def play(self):
        print("Saved game")
"""
        execution_result = {
            'success': True,
            'stdout': 'Saved game\n',
            'stderr': '',
            'returncode': 0,
            'execution_time': 0.1
        }

        saved_dir = game_generator.save_game(code, execution_result, temp_game_dir)

        assert saved_dir.exists()
        assert (saved_dir / "game.py").exists()
        assert (saved_dir / "execution_results.json").exists()

        # Check code was saved correctly
        saved_code = (saved_dir / "game.py").read_text()
        assert 'class Game' in saved_code

        # Check results were saved correctly
        import json
        saved_results = json.loads((saved_dir / "execution_results.json").read_text())
        assert saved_results['success'] is True
        assert saved_results['stdout'] == 'Saved game\n'


class TestRealGameExamples:
    """Tests with realistic game code examples"""

    def test_conways_game_of_life(self, game_generator):
        """Test execution of Conway's Game of Life"""
        code = """class Game:
    def __init__(self):
        self.grid = [
            [0, 1, 0, 0, 0],
            [1, 1, 0, 0, 0],
            [0, 0, 0, 1, 0],
            [0, 0, 1, 1, 0],
            [0, 0, 0, 0, 0]
        ]
        self.generation = 0

    def play(self):
        for i in range(3):
            self.generation += 1
            print(f"Generation {self.generation}:")
            for row in self.grid:
                print(' '.join(str(cell) for cell in row))
            print()

if __name__ == "__main__":
    game = Game()
    game.play()
"""
        result = game_generator.execute_game(code, timeout=5)

        assert result['success'] is True
        assert result['returncode'] == 0
        assert 'Generation 1:' in result['stdout']
        assert 'Generation 3:' in result['stdout']

    def test_simple_particle_simulation(self, game_generator):
        """Test execution of simple particle simulation"""
        code = """class Game:
    def __init__(self):
        self.particles = [(0, 0), (5, 5), (10, 10)]
        self.step = 0

    def play(self):
        for step in range(3):
            self.step = step + 1
            print(f"Step {self.step}:")
            for i, (x, y) in enumerate(self.particles):
                new_x = x + 1
                new_y = y + 1
                self.particles[i] = (new_x, new_y)
                print(f"  Particle {i}: ({new_x}, {new_y})")
            print()

if __name__ == "__main__":
    game = Game()
    game.play()
"""
        result = game_generator.execute_game(code, timeout=5)

        assert result['success'] is True
        assert 'Step 1:' in result['stdout']
        assert 'Step 3:' in result['stdout']
        assert 'Particle 0:' in result['stdout']

    def test_cellular_automata(self, game_generator):
        """Test execution of 1D cellular automata"""
        code = """class Game:
    def __init__(self):
        self.cells = [0, 1, 1, 0, 1, 0, 0, 1]
        self.generation = 0

    def play(self):
        for gen in range(3):
            self.generation = gen + 1
            print(f"Generation {self.generation}: {' '.join(str(c) for c in self.cells)}")
            # Simple rule: cell becomes 1 if neighbor sum is odd
            new_cells = []
            for i in range(len(self.cells)):
                left = self.cells[i-1] if i > 0 else 0
                right = self.cells[i+1] if i < len(self.cells)-1 else 0
                new_cells.append(1 if (left + self.cells[i] + right) % 2 == 1 else 0)
            self.cells = new_cells

if __name__ == "__main__":
    game = Game()
    game.play()
"""
        result = game_generator.execute_game(code, timeout=5)

        assert result['success'] is True
        assert 'Generation 1:' in result['stdout']
        assert 'Generation 2:' in result['stdout']
        assert 'Generation 3:' in result['stdout']

    def test_infinite_loop_timeout(self, game_generator):
        """Test that infinite loops are properly caught by timeout"""
        code = """class Game:
    def play(self):
        while True:
            pass

if __name__ == "__main__":
    game = Game()
    game.play()
"""
        result = game_generator.execute_game(code, timeout=1)

        assert result['success'] is False
        assert 'timeout' in result['stderr'].lower()
        assert result['returncode'] == -1

    def test_runtime_error_capture(self, game_generator):
        """Test that runtime errors are captured"""
        code = """class Game:
    def play(self):
        x = 1 / 0  # Division by zero

if __name__ == "__main__":
    game = Game()
    game.play()
"""
        result = game_generator.execute_game(code, timeout=5)

        assert result['success'] is False
        assert result['returncode'] != 0
        assert 'ZeroDivisionError' in result['stderr'] or 'error' in result['stderr'].lower()


class TestIntegration:
    """Integration tests for full workflow"""

    @pytest.mark.integration
    def test_full_workflow_with_mocks(self, game_generator, temp_game_dir):
        """Test full workflow: design -> execute -> save"""
        prompt = "Create a simple counting game"

        # Design game (mocked)
        design_result = game_generator.design_game(prompt)
        assert design_result['valid'] is True

        # Execute game
        execution_result = game_generator.execute_game(design_result['code'])

        # Save game
        saved_dir = game_generator.save_game(
            design_result['code'],
            execution_result,
            temp_game_dir
        )

        assert saved_dir.exists()
        assert (saved_dir / "game.py").exists()
        assert (saved_dir / "execution_results.json").exists()

    @pytest.mark.integration
    def test_full_workflow_with_real_game(self, game_generator, temp_game_dir):
        """Test full workflow with a realistic game code"""
        # Real game code (not from API, but realistic)
        code = """class Game:
    def __init__(self):
        self.grid_size = 5
        self.grid = [[0 for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        self.grid[2][2] = 1  # Center cell alive

    def play(self):
        print("Initial grid:")
        self.print_grid()
        print("\\nAfter 2 generations:")
        for gen in range(2):
            self.next_generation()
            self.print_grid()
            print()

    def print_grid(self):
        for row in self.grid:
            print(' '.join(str(cell) for cell in row))

    def next_generation(self):
        new_grid = [[0 for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                neighbors = sum(self.grid[(i+di)%self.grid_size][(j+dj)%self.grid_size]
                               for di in [-1,0,1] for dj in [-1,0,1] if (di,dj) != (0,0))
                if self.grid[i][j] == 1:
                    new_grid[i][j] = 1 if neighbors in [2,3] else 0
                else:
                    new_grid[i][j] = 1 if neighbors == 3 else 0
        self.grid = new_grid

if __name__ == "__main__":
    game = Game()
    game.play()
"""

        # Validate structure
        is_valid, error = game_generator.validate_game_structure(code)
        assert is_valid is True, f"Structure validation failed: {error}"

        # Execute
        execution_result = game_generator.execute_game(code)
        assert execution_result['success'] is True
        assert 'Initial grid:' in execution_result['stdout']
        assert 'After 2 generations:' in execution_result['stdout']

        # Save
        saved_dir = game_generator.save_game(code, execution_result, temp_game_dir)

        # Verify saved files
        assert saved_dir.exists()
        saved_code = (saved_dir / "game.py").read_text()
        assert 'class Game' in saved_code
        assert 'def play(self):' in saved_code

        import json
        saved_results = json.loads((saved_dir / "execution_results.json").read_text())
        assert saved_results['success'] is True

