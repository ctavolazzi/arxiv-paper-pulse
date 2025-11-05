# ImageGenerator Test Suite Guide

## Overview

The ImageGenerator test suite provides comprehensive testing of the image generation module with both mocked and live API tests. Tests can optionally save actual images to a visible directory so you can verify they were generated correctly.

## Running Tests

### Run All ImageGenerator Tests
```bash
pytest tests/test_image_generator.py -v
```

### Run Only Tests That Save Images
```bash
pytest -m saves_images -v
```

### Run Tests with Live API (requires GEMINI_API_KEY)
```bash
pytest -m "saves_images and live_api" -v
```

### Run Specific Test Classes
```bash
# Unit tests (mocked)
pytest tests/test_image_generator.py::TestImageGeneratorInitialization -v

# Save functionality tests
pytest tests/test_image_generator.py::TestSaveImage -v

# Integration tests
pytest tests/test_image_generator.py::TestIntegration -v

# Tests that save visible images
pytest tests/test_image_generator.py::TestImageSaving -v
```

### Run with Coverage
```bash
pytest tests/test_image_generator.py --cov=arxiv_paper_pulse.image_generator --cov-report=html
```

## Test Categories

### 1. Unit Tests (Mocked - Fast)
These tests use mocked API responses and run quickly:
- `TestImageGeneratorInitialization` - Module initialization
- `TestGenerateFromText` - Text-to-image generation
- `TestGenerateFromTextAndImage` - Image editing
- `TestSaveImage` - Image saving functionality
- `TestGenerateAndSave` - Combined operations
- `TestImageOutputLocation` - Directory structure

**No images saved** - Uses temporary directories that are cleaned up.

### 2. Integration Tests (Mocked)
Full workflow tests using mocks:
- `TestIntegration` - Complete generate → save → verify workflows

**Images saved to temp directories** - Cleaned up after tests.

### 3. Visual Tests (Saves Images You Can See)
Tests that save images to `tests/test_images/` so you can view them:

#### Without API (Fast):
```bash
pytest tests/test_image_generator.py::TestImageSaving::test_save_test_image_visible -v -s
```
- Creates a simple test image and saves it
- Fast, no API calls
- **Image saved to:** `tests/test_images/test_saved_image.png`

#### With Live API:
```bash
# Requires GEMINI_API_KEY
pytest tests/test_image_generator.py::TestImageSaving::test_generate_and_save_real_image -v -s
```
- Generates a real image using Gemini API
- **Image saved to:** `tests/test_images/test_real_generated_image.png`

#### Multiple Test Images:
```bash
pytest tests/test_image_generator.py::TestImageSaving::test_generate_multiple_test_images -v -s
```
- Generates 3 different test images
- **Images saved to:**
  - `tests/test_images/test_circle.png`
  - `tests/test_images/test_square.png`
  - `tests/test_images/test_triangle.png`

## Test Markers

Tests are marked for easy filtering:

- `@pytest.mark.saves_images` - Test saves actual image files
- `@pytest.mark.live_api` - Test requires live API calls (needs GEMINI_API_KEY)

## Viewing Generated Images

All images from `saves_images` tests are saved to:
```
tests/test_images/
```

You can view these images in your file browser or image viewer to verify they were generated correctly.

## Test Coverage

The test suite covers:

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

## Running Test Suite Examples

### Quick Test (Mocked - Fast)
```bash
# All mocked tests - runs in seconds
pytest tests/test_image_generator.py -v -m "not saves_images"
```

### Full Test Suite (Including Visual)
```bash
# All tests including those that save images
pytest tests/test_image_generator.py -v
```

### Live API Test Suite
```bash
# Requires GEMINI_API_KEY
export GEMINI_API_KEY=your_key
pytest tests/test_image_generator.py -v -m "saves_images and live_api"
```

## Test Images Directory

Images saved during tests are in `tests/test_images/`:
- Visible and easy to find
- Not cleaned up automatically (so you can view them)
- Can be manually deleted if needed
- See `tests/test_images/README.md` for details

## Continuous Integration

For CI/CD, run without live API tests:
```bash
pytest tests/test_image_generator.py -v -m "not live_api"
```

Or skip tests that save images:
```bash
pytest tests/test_image_generator.py -v -m "not saves_images"
```

## Troubleshooting

### Tests fail with "No image data found in response"
- Mock setup might be incorrect
- Check that `mock_gemini_client` fixture is working

### Live API tests skipped
- Set `GEMINI_API_KEY` environment variable
- Check API quota hasn't been exceeded

### Images not visible in tests/test_images/
- Make sure tests with `@pytest.mark.saves_images` ran
- Check directory exists: `tests/test_images/`
- Run with `-s` flag to see print statements: `pytest -v -s`

