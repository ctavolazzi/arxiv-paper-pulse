# ImageGenerator Module - Complete Guide

## What This Module Does

The `ImageGenerator` module is a standalone, modular component that generates images using Google's Gemini 2.5 Flash Image Preview API. It's designed to be:
- **Modular**: Can be used independently or composed with other systems
- **Configurable**: Uses centralized configuration
- **Tested**: Comprehensive test suite with visible image outputs
- **Tracked**: Automatic API call logging for analysis

## Quick Start

### Basic Usage

```python
from arxiv_paper_pulse.image_generator import ImageGenerator

# Initialize (uses config automatically)
generator = ImageGenerator()

# Generate image from text
image = generator.generate_from_text("A red circle on white background")

# Save image
saved_path = generator.save_image(image, "my_image.png")

# Or generate and save in one step
saved_path = generator.generate_and_save(
    "A blue square with rounded corners",
    "output.png"
)
```

### With Custom Configuration

```python
generator = ImageGenerator(
    api_key="your_key",           # Optional: defaults to config
    model="gemini-2.5-flash-image-preview",  # Optional: defaults to config
    output_dir="./custom_images",  # Optional: defaults to config
    log_dir="./custom_logs"       # Optional: defaults to config
)
```

## Features

### 1. Text-to-Image Generation
Generate images from text prompts using Gemini API:
- High-quality 1024x1024 pixel images
- Support for various styles (photorealistic, stylized, abstract, etc.)
- Automatic image data extraction and validation

### 2. Image Editing
Edit existing images with text prompts:
```python
from PIL import Image

base_image = Image.open("existing_image.png")
edited_image = generator.generate_from_text_and_image(
    "Add a blue border around this image",
    base_image
)
```

### 3. Automatic Logging
Every API call is automatically logged with:
- Timestamp
- Prompt text and length
- Response time
- Token usage
- Image metadata
- File information

Logs are saved to: `arxiv_paper_pulse/data/api_logs/image_api_calls_YYYYMMDD.jsonl`

### 4. File Management
- Automatic directory creation
- Auto-generated filenames with timestamps
- Configurable output directory
- Validated image saving

## Configuration

### Environment Variables

All configuration is in `arxiv_paper_pulse/config.py`:

```python
IMAGE_OUTPUT_DIR = "arxiv_paper_pulse/data/generated_images"  # Where images are saved
IMAGE_API_LOG_DIR = "arxiv_paper_pulse/data/api_logs"          # Where logs are saved
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")                    # API key from .env
```

### Output Directories

**Generated Images:** `arxiv_paper_pulse/data/generated_images/`
- All generated images saved here
- Clearly labeled folder
- README.md explains purpose

**API Logs:** `arxiv_paper_pulse/data/api_logs/`
- JSONL format (one JSON object per line)
- Daily log files: `image_api_calls_YYYYMMDD.jsonl`
- Complete API call metadata

**Test Images:** `tests/test_images/`
- Images generated during tests
- Visible and easy to find
- Used for verification

## API Methods

### `generate_from_text(prompt: str, log_call: bool = True) -> PIL.Image`
Generate an image from a text prompt.

**Args:**
- `prompt`: Text description of the image
- `log_call`: Whether to log this API call (default: True)

**Returns:** PIL.Image object

**Example:**
```python
image = generator.generate_from_text("A minimalist logo design")
```

### `generate_from_text_and_image(prompt: str, base_image: PIL.Image) -> PIL.Image`
Edit an existing image with a text prompt.

**Args:**
- `prompt`: Edit instructions
- `base_image`: PIL Image to edit

**Returns:** PIL.Image object with edits applied

### `save_image(image: PIL.Image, filepath: str = None) -> str`
Save a PIL Image to file.

**Args:**
- `image`: PIL Image object
- `filepath`: Optional path (auto-generates if None)

**Returns:** Path to saved file

**Example:**
```python
# Auto-filename
path = generator.save_image(image)  # Uses timestamp

# Custom filename
path = generator.save_image(image, "my_image.png")
```

### `generate_and_save(prompt: str, output_path: str, log_call: bool = True) -> str`
Convenience method: generate and save in one step.

**Example:**
```python
path = generator.generate_and_save(
    "A red circle on white background",
    "circle.png"
)
```

## API Call Logging

### Viewing Logs

Use the `explore_api_logs.py` script:

```bash
# Show summary and latest entry
python3 explore_api_logs.py

# Show summary only
python3 explore_api_logs.py summary

# List all entries
python3 explore_api_logs.py list

# Explore specific entry
python3 explore_api_logs.py 0  # Entry #0
```

### Log Entry Structure

Each log entry contains:
```json
{
  "timestamp": "2025-11-01T21:10:00.768528",
  "model": "gemini-2.5-flash-image-preview",
  "prompt": "Your prompt text",
  "prompt_length": 70,
  "response_time_seconds": 5.063,
  "image_size": "1024x1024",
  "image_mode": "RGB",
  "image_data_size_bytes": 331135,
  "response_metadata": {
    "usage": {
      "prompt_token_count": 14,
      "candidates_token_count": 1308,
      "total_token_count": 1322
    },
    "candidate": {
      "finish_reason": "STOP"
    }
  },
  "saved_file": {
    "path": "filename.png",
    "filename": "filename.png",
    "file_size_bytes": 304660,
    "file_size_kb": 297.52
  }
}
```

## Testing

### Test Suite Overview

**Total Tests:** 22 comprehensive tests

**Test Categories:**
1. **Unit Tests (18 tests)** - Mocked, fast execution
2. **Visual Tests (3 tests)** - Save actual images you can see
3. **Integration Tests** - Full workflow verification

### Running Tests

**Run All Tests:**
```bash
pytest tests/test_image_generator.py -v
```

**Run Tests That Save Visible Images:**
```bash
pytest -m saves_images -v -s
```

**Run Live API Tests (requires GEMINI_API_KEY):**
```bash
pytest -m "saves_images and live_api" -v -s
```

**Run Specific Test:**
```bash
pytest tests/test_image_generator.py::TestImageSaving::test_generate_and_save_real_image -v -s
```

### Test Markers

- `@pytest.mark.saves_images` - Test saves visible images
- `@pytest.mark.live_api` - Test requires live API calls

### Test Images Location

Tests that save images write to: `tests/test_images/`

**Test Images Include:**
- `test_saved_image.png` - Simple test image (mocked)
- `test_real_generated_image.png` - Real API-generated image
- `test_test_circle.png` - Red circle test
- `test_test_square.png` - Blue square test
- `test_test_triangle.png` - Green triangle test

### Test Coverage

✅ Module initialization with various configurations
✅ Text-to-image generation
✅ Image editing (text + image)
✅ Image saving with different paths
✅ Auto-filename generation
✅ Directory creation
✅ Full workflow integration
✅ Error handling
✅ File validation
✅ Visible image saving for manual verification
✅ API call logging

## Module Architecture

### Design Principles

1. **Single Responsibility**: Module only handles image generation
2. **Dependency Injection**: Dependencies passed via constructor
3. **Clear Contracts**: Well-defined input/output types
4. **Configuration Management**: Centralized in config.py

### Integration Patterns

**Pattern 1: Direct Usage**
```python
generator = ImageGenerator()
image = generator.generate_from_text(prompt)
```

**Pattern 2: Dependency Injection**
```python
class LootConverter:
    def __init__(self, image_generator: ImageGenerator):
        self.image_generator = image_generator
```

**Pattern 3: Module Composition**
```python
class GameEngine:
    def __init__(self, image_generator: ImageGenerator, loot_converter: LootConverter):
        self.image_generator = image_generator
        self.loot_converter = loot_converter
```

## File Structure

```
arxiv_paper_pulse/
├── image_generator.py          # Main module
├── config.py                   # Configuration
└── data/
    ├── generated_images/       # All generated images
    │   └── README.md
    └── api_logs/               # API call logs
        ├── image_api_calls_YYYYMMDD.jsonl
        └── README.md

tests/
├── test_image_generator.py     # Comprehensive test suite
├── test_images/                # Test-generated images
│   └── README.md
└── test_image_generator_SUITE.md  # Test suite guide
```

## Example Workflows

### Workflow 1: Simple Image Generation
```python
from arxiv_paper_pulse.image_generator import ImageGenerator

generator = ImageGenerator()
image_path = generator.generate_and_save(
    "A minimalist logo for a coffee shop",
    "coffee_logo.png"
)
print(f"Image saved to: {image_path}")
```

### Workflow 2: Batch Generation
```python
generator = ImageGenerator()
prompts = [
    "A red circle",
    "A blue square",
    "A green triangle"
]

for i, prompt in enumerate(prompts):
    path = generator.generate_and_save(prompt, f"shape_{i}.png")
    print(f"Generated: {path}")
```

### Workflow 3: With Logging Analysis
```python
generator = ImageGenerator()
generator.generate_and_save("Test prompt", "test.png")

# View logs
from explore_api_logs import load_logs, show_summary
logs = load_logs()
show_summary(logs)
```

## Integration with Loot Game System

This module is **Layer 1** of the loot-based game system:

**Architecture:**
- Layer 1: ImageGenerator (this module) ✅
- Layer 2: LootConverter (paper → loot conversion) - Coming soon
- Layer 3: Loot Visual Generator (combines Layer 1 + 2)
- Layer 4: Game Mechanics Engine
- Layer 5: Frontend Integration

**Usage in Game:**
```python
# Generate loot card images
generator = ImageGenerator()
loot_converter = LootConverter(image_generator=generator)
loot_card = loot_converter.create_loot_card(paper_data)
# Image automatically generated and saved
```

## API Endpoints

### POST `/api/generate-image`

Generate an image via API.

**Request:**
```json
{
  "prompt": "Your image description"
}
```

**Response:**
```json
{
  "status": "success",
  "image_path": "path/to/image.png",
  "filename": "image.png",
  "output_directory": "arxiv_paper_pulse/data/generated_images"
}
```

## Troubleshooting

### Images Not Generating

1. Check `GEMINI_API_KEY` is set in `.env`
2. Verify API quota hasn't been exceeded
3. Check logs: `python3 explore_api_logs.py`

### Images Not Saving

1. Check output directory exists: `arxiv_paper_pulse/data/generated_images/`
2. Verify write permissions
3. Check disk space

### Logs Not Appearing

1. Check log directory exists: `arxiv_paper_pulse/data/api_logs/`
2. Verify `log_call=True` in method call
3. Check file permissions

## Performance

**Typical Performance:**
- Generation time: 5-7 seconds per image
- Image size: 1024x1024 pixels
- File size: 200KB - 1.5MB (depending on content)

**Optimization Tips:**
- Use shorter prompts for faster generation
- Batch similar prompts
- Reuse images when possible (image editing vs new generation)

## What We Just Built

### Recap of Session

1. **Created ImageGenerator Module** (`arxiv_paper_pulse/image_generator.py`)
   - Text-to-image generation
   - Image editing capabilities
   - Automatic file saving
   - Configuration-driven setup

2. **Set Up Directory Structure**
   - `generated_images/` - All generated images
   - `api_logs/` - API call logs
   - `test_images/` - Test outputs

3. **Implemented API Call Logging**
   - Automatic logging of all API calls
   - JSONL format for easy analysis
   - Explore script for viewing logs
   - Metadata extraction (tokens, timing, etc.)

4. **Created Comprehensive Test Suite**
   - 22 tests covering all functionality
   - Tests that save visible images
   - Mock tests for fast execution
   - Live API tests for real verification

5. **Added Configuration Support**
   - Centralized config in `config.py`
   - Environment variable support
   - Flexible directory configuration

6. **Created Documentation**
   - Test suite guide
   - Directory READMEs
   - API documentation
   - Integration examples

### Current State

✅ **Module:** Fully functional
✅ **Tests:** 22 tests, all passing
✅ **Logging:** Working and tested
✅ **Documentation:** Complete
✅ **Images Generated:** Multiple test images created
✅ **Ready for Integration:** Can be used in Layer 2 (Loot Converter)

## Next Steps

To continue building the loot game system:

1. **Layer 2: Paper-to-Loot Converter**
   - Transform ArXiv papers into game items
   - Calculate rarity based on paper properties
   - Generate game stats

2. **Layer 3: Loot Visual Generator**
   - Combine ImageGenerator + LootConverter
   - Generate loot card images
   - Style consistency

3. **Integration**
   - Connect to existing paper processing
   - Frontend display
   - Game mechanics

## Quick Reference

**Key Files:**
- `arxiv_paper_pulse/image_generator.py` - Main module
- `arxiv_paper_pulse/config.py` - Configuration
- `tests/test_image_generator.py` - Test suite
- `explore_api_logs.py` - Log viewer

**Key Directories:**
- `arxiv_paper_pulse/data/generated_images/` - Generated images
- `arxiv_paper_pulse/data/api_logs/` - API logs
- `tests/test_images/` - Test images

**Quick Commands:**
```bash
# Generate image
python3 -c "from arxiv_paper_pulse.image_generator import ImageGenerator; \
    ImageGenerator().generate_and_save('Test', 'test.png')"

# View logs
python3 explore_api_logs.py

# Run tests
pytest tests/test_image_generator.py -v

# Run tests that save images
pytest -m saves_images -v -s
```

