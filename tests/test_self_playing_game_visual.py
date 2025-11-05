# tests/test_self_playing_game_visual.py
"""
Visual tests for self-playing game system.
These tests generate actual game outputs that can be visualized.
"""

import pytest
from pathlib import Path
import json
from arxiv_paper_pulse.self_playing_game import SelfDesigningGame
import tempfile


@pytest.fixture
def visual_test_dir(tmp_path):
    """Directory for visual test outputs"""
    visual_dir = tmp_path / "visual_tests"
    visual_dir.mkdir(parents=True, exist_ok=True)
    return visual_dir


@pytest.mark.visual
def test_conways_game_of_life_visual(visual_test_dir):
    """Generate Conway's Game of Life and save output for visualization"""
    code = """class Game:
    def __init__(self):
        self.grid = [
            [0, 1, 0, 0, 0, 0, 0],
            [1, 1, 0, 0, 0, 0, 0],
            [0, 0, 0, 1, 0, 0, 0],
            [0, 0, 1, 1, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 1, 1],
            [0, 0, 0, 0, 0, 1, 0]
        ]
        self.generation = 0

    def play(self):
        for i in range(5):
            self.generation += 1
            print(f"Generation {self.generation}:")
            for row in self.grid:
                print(" ".join("█" if cell else "░" for cell in row))
            print()
            # Simple evolution (not full Conway's rules for demo)
            new_grid = [row[:] for row in self.grid]
            for y in range(len(self.grid)):
                for x in range(len(self.grid[0])):
                    neighbors = sum(1 for dy in [-1,0,1] for dx in [-1,0,1]
                                   if (dy,dx) != (0,0) and 0 <= y+dy < len(self.grid)
                                   and 0 <= x+dx < len(self.grid[0])
                                   and self.grid[y+dy][x+dx] == 1)
                    if self.grid[y][x] == 1:
                        new_grid[y][x] = 1 if neighbors in [2,3] else 0
                    else:
                        new_grid[y][x] = 1 if neighbors == 3 else 0
            self.grid = new_grid

if __name__ == "__main__":
    game = Game()
    game.play()
"""

    generator = SelfDesigningGame(output_dir=str(visual_test_dir))
    result = generator.execute_game(code)

    # Save output
    output_file = visual_test_dir / "conway_output.txt"
    output_file.write_text(result['stdout'])

    # Save as JSON for visualization
    visual_data = {
        'test_name': 'Conway\'s Game of Life',
        'success': result['success'],
        'output': result['stdout'],
        'execution_time': result['execution_time']
    }

    json_file = visual_test_dir / "conway_data.json"
    json_file.write_text(json.dumps(visual_data, indent=2))

    assert result['success'] is True
    return visual_test_dir


@pytest.mark.visual
def test_particle_simulation_visual(visual_test_dir):
    """Generate particle simulation and save output"""
    code = """class Game:
    def __init__(self):
        self.particles = [
            {'x': 0, 'y': 0, 'vx': 1, 'vy': 1},
            {'x': 5, 'y': 5, 'vx': -1, 'vy': 1},
            {'x': 10, 'y': 10, 'vx': 1, 'vy': -1}
        ]
        self.step = 0

    def play(self):
        for step in range(8):
            self.step = step + 1
            print(f"Step {self.step}:")
            for i, p in enumerate(self.particles):
                p['x'] += p['vx']
                p['y'] += p['vy']
                print(f"  Particle {i}: position=({p['x']:3d}, {p['y']:3d}) velocity=({p['vx']:+2d}, {p['vy']:+2d})")
            print()

if __name__ == "__main__":
    game = Game()
    game.play()
"""

    generator = SelfDesigningGame(output_dir=str(visual_test_dir))
    result = generator.execute_game(code)

    visual_data = {
        'test_name': 'Particle Simulation',
        'success': result['success'],
        'output': result['stdout'],
        'execution_time': result['execution_time']
    }

    json_file = visual_test_dir / "particle_data.json"
    json_file.write_text(json.dumps(visual_data, indent=2))

    assert result['success'] is True
    return visual_test_dir


@pytest.mark.visual
def test_cellular_automata_visual(visual_test_dir):
    """Generate cellular automata and save output"""
    code = """class Game:
    def __init__(self):
        self.cells = [0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1]
        self.generation = 0

    def play(self):
        for gen in range(10):
            self.generation = gen + 1
            visual = "".join("█" if c else "░" for c in self.cells)
            print(f"Generation {self.generation:2d}: {visual}")
            # Rule: cell becomes 1 if neighbor sum is odd
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

    generator = SelfDesigningGame(output_dir=str(visual_test_dir))
    result = generator.execute_game(code)

    visual_data = {
        'test_name': '1D Cellular Automata',
        'success': result['success'],
        'output': result['stdout'],
        'execution_time': result['execution_time']
    }

    json_file = visual_test_dir / "automata_data.json"
    json_file.write_text(json.dumps(visual_data, indent=2))

    assert result['success'] is True
    return visual_test_dir

