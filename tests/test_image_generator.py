# tests/test_image_generator.py

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from PIL import Image as PILImage
import io

from arxiv_paper_pulse.image_generator import ImageGenerator


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini client for image generation testing"""
    with patch('arxiv_paper_pulse.image_generator.genai.Client') as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock response with inline image data
        mock_part = Mock()
        mock_part.inline_data = Mock()
        # Create a simple test image as bytes
        test_image = PILImage.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        test_image.save(img_bytes, format='PNG')
        mock_part.inline_data.data = img_bytes.getvalue()

        mock_content = Mock()
        mock_content.parts = [mock_part]

        mock_candidate = Mock()
        mock_candidate.content = mock_content

        mock_response = Mock()
        mock_response.candidates = [mock_candidate]

        mock_client.models.generate_content.return_value = mock_response

        yield mock_client


@pytest.fixture
def temp_image_dir(tmp_path):
    """Temporary directory for image output"""
    img_dir = tmp_path / "generated_images"
    img_dir.mkdir(parents=True, exist_ok=True)
    return img_dir


@pytest.fixture
def image_generator(mock_gemini_client, temp_image_dir, monkeypatch):
    """Create ImageGenerator instance with mocked client and temp directory"""
    monkeypatch.setattr('arxiv_paper_pulse.config.IMAGE_OUTPUT_DIR', str(temp_image_dir))
    monkeypatch.setattr('arxiv_paper_pulse.config.GEMINI_API_KEY', 'test_key')

    generator = ImageGenerator(output_dir=str(temp_image_dir))
    generator.client = mock_gemini_client
    return generator


class TestImageGeneratorInitialization:
    """Tests for ImageGenerator initialization"""

    def test_init_with_default_config(self, monkeypatch):
        """Test initialization with default configuration"""
        monkeypatch.setattr('arxiv_paper_pulse.config.GEMINI_API_KEY', 'test_key')
        monkeypatch.setattr('arxiv_paper_pulse.config.IMAGE_OUTPUT_DIR', 'test_dir')

        with patch('arxiv_paper_pulse.image_generator.genai.Client') as mock_client:
            generator = ImageGenerator()

            assert generator.api_key == 'test_key'
            assert generator.model == 'gemini-2.5-flash-image-preview'
            assert Path(generator.output_dir).name == Path('test_dir').name
            mock_client.assert_called_once_with(api_key='test_key')

    def test_init_with_custom_params(self, temp_image_dir):
        """Test initialization with custom parameters"""
        with patch('arxiv_paper_pulse.image_generator.genai.Client') as mock_client:
            generator = ImageGenerator(
                api_key='custom_key',
                model='custom-model',
                output_dir=str(temp_image_dir)
            )

            assert generator.api_key == 'custom_key'
            assert generator.model == 'custom-model'
            assert generator.output_dir == temp_image_dir
            mock_client.assert_called_once_with(api_key='custom_key')

    def test_output_directory_created(self, tmp_path):
        """Test that output directory is created if it doesn't exist"""
        new_dir = tmp_path / "new_images"

        with patch('arxiv_paper_pulse.image_generator.genai.Client'):
            generator = ImageGenerator(output_dir=str(new_dir))

            assert new_dir.exists()
            assert new_dir.is_dir()


class TestGenerateFromText:
    """Tests for text-to-image generation"""

    def test_generate_from_text_success(self, image_generator, mock_gemini_client):
        """Test successful image generation from text prompt"""
        prompt = "A red square on white background"

        image = image_generator.generate_from_text(prompt)

        assert isinstance(image, PILImage.Image)
        assert image.size == (100, 100)
        mock_gemini_client.models.generate_content.assert_called_once()
        call_args = mock_gemini_client.models.generate_content.call_args
        assert call_args[1]['model'] == 'gemini-2.5-flash-image-preview'
        assert call_args[1]['contents'] == [prompt]

    def test_generate_from_text_no_image_data(self, image_generator, mock_gemini_client):
        """Test error handling when no image data in response"""
        # Mock response with no inline_data
        mock_part = Mock()
        mock_part.inline_data = None

        mock_content = Mock()
        mock_content.parts = [mock_part]

        mock_candidate = Mock()
        mock_candidate.content = mock_content

        mock_response = Mock()
        mock_response.candidates = [mock_candidate]

        mock_gemini_client.models.generate_content.return_value = mock_response

        with pytest.raises(ValueError, match="No image data found in response"):
            image_generator.generate_from_text("test prompt")

    def test_generate_from_text_empty_response(self, image_generator, mock_gemini_client):
        """Test error handling with empty response"""
        mock_response = Mock()
        mock_response.candidates = []
        mock_gemini_client.models.generate_content.return_value = mock_response

        with pytest.raises(IndexError):
            image_generator.generate_from_text("test prompt")


class TestGenerateFromTextAndImage:
    """Tests for image editing functionality"""

    def test_generate_from_text_and_image_success(self, image_generator, mock_gemini_client):
        """Test successful image editing"""
        prompt = "Add a blue circle"
        base_image = PILImage.new('RGB', (200, 200), color='white')

        image = image_generator.generate_from_text_and_image(prompt, base_image)

        assert isinstance(image, PILImage.Image)
        mock_gemini_client.models.generate_content.assert_called_once()
        call_args = mock_gemini_client.models.generate_content.call_args
        assert call_args[1]['model'] == 'gemini-2.5-flash-image-preview'
        # Should pass both prompt and image
        contents = call_args[1]['contents']
        assert len(contents) == 2
        assert contents[0] == prompt
        assert contents[1] == base_image

    def test_generate_from_text_and_image_no_data(self, image_generator, mock_gemini_client):
        """Test error handling when no image data in edited response"""
        # Mock response with no inline_data
        mock_part = Mock()
        mock_part.inline_data = None

        mock_content = Mock()
        mock_content.parts = [mock_part]

        mock_candidate = Mock()
        mock_candidate.content = mock_content

        mock_response = Mock()
        mock_response.candidates = [mock_candidate]

        mock_gemini_client.models.generate_content.return_value = mock_response

        base_image = PILImage.new('RGB', (100, 100), color='white')

        with pytest.raises(ValueError, match="No image data found in response"):
            image_generator.generate_from_text_and_image("edit", base_image)


class TestSaveImage:
    """Tests for image saving functionality"""

    def test_save_image_with_filepath(self, image_generator, temp_image_dir):
        """Test saving image with specified filepath"""
        image = PILImage.new('RGB', (100, 100), color='blue')
        filepath = temp_image_dir / "test_image.png"

        saved_path = image_generator.save_image(image, str(filepath))

        assert saved_path == str(filepath)
        assert filepath.exists()
        # Verify it's a valid image
        loaded_image = PILImage.open(filepath)
        assert loaded_image.size == (100, 100)

    def test_save_image_auto_filename(self, image_generator, temp_image_dir):
        """Test saving image with auto-generated filename"""
        image = PILImage.new('RGB', (100, 100), color='green')

        saved_path = image_generator.save_image(image)

        assert saved_path.startswith(str(temp_image_dir))
        assert saved_path.endswith('.png')
        assert 'generated_image_' in saved_path
        assert Path(saved_path).exists()

    def test_save_image_creates_directories(self, image_generator, temp_image_dir):
        """Test that save_image creates parent directories if needed"""
        image = PILImage.new('RGB', (50, 50), color='yellow')
        nested_path = temp_image_dir / "subdir" / "nested" / "image.png"

        saved_path = image_generator.save_image(image, str(nested_path))

        assert nested_path.parent.exists()
        assert nested_path.exists()


class TestGenerateAndSave:
    """Tests for combined generate and save functionality"""

    def test_generate_and_save(self, image_generator, mock_gemini_client, temp_image_dir):
        """Test generate_and_save convenience method"""
        prompt = "A colorful test image"
        output_path = temp_image_dir / "test_output.png"

        saved_path = image_generator.generate_and_save(prompt, str(output_path))

        assert saved_path == str(output_path)
        assert output_path.exists()
        mock_gemini_client.models.generate_content.assert_called_once()

    def test_generate_and_save_creates_dirs(self, image_generator, mock_gemini_client, temp_image_dir):
        """Test that generate_and_save creates directories"""
        prompt = "Another test image"
        nested_path = temp_image_dir / "new" / "dir" / "output.png"

        saved_path = image_generator.generate_and_save(prompt, str(nested_path))

        assert nested_path.exists()
        assert saved_path == str(nested_path)


class TestImageOutputLocation:
    """Tests for image output directory structure"""

    def test_default_output_directory_exists(self):
        """Test that default output directory is in expected location"""
        with patch('arxiv_paper_pulse.image_generator.genai.Client'):
            generator = ImageGenerator()

            # Should be in arxiv_paper_pulse/data/generated_images
            assert 'generated_images' in str(generator.output_dir)
            assert generator.output_dir.exists()

    def test_images_saved_to_correct_location(self, image_generator, temp_image_dir):
        """Test that images are saved to the configured output directory"""
        image = PILImage.new('RGB', (100, 100), color='purple')

        saved_path = image_generator.save_image(image)

        assert Path(saved_path).parent == temp_image_dir
        assert temp_image_dir in Path(saved_path).parents

    def test_output_directory_is_findable(self, image_generator, temp_image_dir):
        """Test that the output directory is clearly labeled and findable"""
        # Verify the directory name contains "generated_images"
        assert 'generated_images' in str(temp_image_dir.name) or 'generated_images' in str(temp_image_dir)

        # Verify README or marker file could be added if needed
        # (This is a test that the structure supports easy location)
        assert temp_image_dir.is_dir()


class TestIntegration:
    """Integration tests for full workflow"""

    def test_full_generate_save_workflow(self, image_generator, mock_gemini_client, temp_image_dir):
        """Test complete workflow: generate → save → verify"""
        prompt = "Integration test image"
        output_path = temp_image_dir / "integration_test.png"

        # Generate and save
        saved_path = image_generator.generate_and_save(prompt, str(output_path))

        # Verify file exists
        assert Path(saved_path).exists()

        # Verify it's a valid image
        loaded = PILImage.open(saved_path)
        assert isinstance(loaded, PILImage.Image)
        assert loaded.size == (100, 100)  # Size from mock

    def test_multiple_generations_different_files(self, image_generator, mock_gemini_client, temp_image_dir):
        """Test generating multiple images creates different files"""
        prompts = ["Image 1", "Image 2", "Image 3"]

        saved_paths = []
        for i, prompt in enumerate(prompts):
            path = temp_image_dir / f"image_{i}.png"
            saved = image_generator.generate_and_save(prompt, str(path))
            saved_paths.append(saved)

        # All files should exist
        for path in saved_paths:
            assert Path(path).exists()

        # All paths should be different
        assert len(set(saved_paths)) == len(saved_paths)


class TestImageSaving:
    """Tests that save actual image files to visible locations"""

    @pytest.fixture
    def test_images_dir(self):
        """Directory for test images that will be kept"""
        test_dir = Path(__file__).parent / "test_images"
        test_dir.mkdir(exist_ok=True)
        return test_dir

    @pytest.mark.saves_images
    def test_save_test_image_visible(self, test_images_dir):
        """Save a test image to test_images directory so it's visible"""
        from arxiv_paper_pulse.image_generator import ImageGenerator

        # Create a simple test image
        test_image = PILImage.new('RGB', (200, 200), color='blue')

        # Save to visible test_images directory
        output_path = test_images_dir / "test_saved_image.png"
        test_image.save(output_path)

        # Verify it exists and is valid
        assert output_path.exists()
        loaded = PILImage.open(output_path)
        assert loaded.size == (200, 200)
        assert loaded.mode == 'RGB'

        print(f"\n✅ Test image saved to: {output_path}")
        print(f"   You can view it at: {output_path.absolute()}")

    @pytest.mark.saves_images
    @pytest.mark.live_api
    def test_generate_and_save_real_image(self, test_images_dir, monkeypatch):
        """Generate a real image using API and save to test_images directory"""
        import os
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set, skipping live API test")

        from arxiv_paper_pulse.image_generator import ImageGenerator

        # Use test_images directory
        monkeypatch.setattr('arxiv_paper_pulse.config.IMAGE_OUTPUT_DIR', str(test_images_dir))

        generator = ImageGenerator(output_dir=str(test_images_dir))
        prompt = "A simple test image: a red square on white background"

        output_path = test_images_dir / "test_real_generated_image.png"
        saved_path = generator.generate_and_save(prompt, str(output_path), log_call=True)

        # Verify it exists and is valid
        assert Path(saved_path).exists()
        loaded = PILImage.open(saved_path)
        assert isinstance(loaded, PILImage.Image)
        assert loaded.size[0] > 0 and loaded.size[1] > 0

        print(f"\n✅ Real image generated and saved to: {saved_path}")
        print(f"   You can view it at: {Path(saved_path).absolute()}")

    @pytest.mark.saves_images
    @pytest.mark.live_api
    def test_generate_multiple_test_images(self, test_images_dir, monkeypatch):
        """Generate multiple test images with different prompts"""
        import os
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set, skipping live API test")

        from arxiv_paper_pulse.image_generator import ImageGenerator
        import time

        # Use test_images directory
        monkeypatch.setattr('arxiv_paper_pulse.config.IMAGE_OUTPUT_DIR', str(test_images_dir))

        generator = ImageGenerator(output_dir=str(test_images_dir))
        test_prompts = [
            ("Test Circle", "A red circle on white background"),
            ("Test Square", "A blue square with rounded corners"),
            ("Test Triangle", "A green triangle on transparent background")
        ]

        saved_paths = []
        for name, prompt in test_prompts:
            output_path = test_images_dir / f"test_{name.lower().replace(' ', '_')}.png"
            saved_path = generator.generate_and_save(prompt, str(output_path), log_call=True)
            saved_paths.append(saved_path)

            # Verify it exists
            assert Path(saved_path).exists()

            # Small delay to avoid rate limits
            time.sleep(2)

        print(f"\n✅ Generated {len(saved_paths)} test images:")
        for path in saved_paths:
            print(f"   - {Path(path).name} ({Path(path).absolute()})")

