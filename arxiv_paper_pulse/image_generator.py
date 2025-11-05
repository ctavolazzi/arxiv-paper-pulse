# arxiv_paper_pulse/image_generator.py
from google import genai
from PIL import Image
from io import BytesIO
from pathlib import Path
import json
import time
from datetime import datetime
from . import config

class ImageGenerator:
    """
    Standalone image generation module using Gemini 2.5-flash-image-preview.
    Modular component that can be used independently or composed with other systems.

    Images are saved to: arxiv_paper_pulse/data/generated_images/
    """

    def __init__(self, api_key=None, model=None, output_dir=None, log_dir=None):
        self.api_key = api_key or config.GEMINI_API_KEY
        self.model = model or "gemini-2.5-flash-image-preview"
        self.output_dir = Path(output_dir or config.IMAGE_OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir = Path(log_dir or config.IMAGE_API_LOG_DIR)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.client = genai.Client(api_key=self.api_key)

    def generate_from_text(self, prompt: str, log_call=True) -> Image.Image:
        """
        Generate an image from a text prompt.

        Args:
            prompt: Text description of the image to generate
            log_call: Whether to log API call data (default: True)

        Returns:
            PIL Image object
        """
        start_time = time.time()
        timestamp = datetime.now().isoformat()

        response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt]
        )

        response_time = time.time() - start_time

        image = None
        image_data = None

        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image_data = part.inline_data.data
                image = Image.open(BytesIO(image_data))
                break

        if image is None:
            raise ValueError("No image data found in response")

        # Log API call data
        if log_call:
            self._log_api_call({
                'timestamp': timestamp,
                'model': self.model,
                'prompt': prompt,
                'prompt_length': len(prompt),
                'response_time_seconds': round(response_time, 3),
                'image_size': f"{image.size[0]}x{image.size[1]}",
                'image_mode': image.mode,
                'image_data_size_bytes': len(image_data) if image_data else None,
                'response_metadata': self._extract_response_metadata(response)
            })

        return image

    def _extract_response_metadata(self, response):
        """Extract useful metadata from API response"""
        metadata = {}

        try:
            # Extract usage metadata
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage_meta = response.usage_metadata
                metadata['usage'] = {
                    'prompt_token_count': getattr(usage_meta, 'prompt_token_count', None),
                    'candidates_token_count': getattr(usage_meta, 'candidates_token_count', None),
                    'total_token_count': getattr(usage_meta, 'total_token_count', None)
                }

            # Extract candidate metadata
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                candidate_meta = {
                    'finish_reason': getattr(candidate, 'finish_reason', None),
                    'finish_message': getattr(candidate, 'finish_message', None)
                }

                # Safely extract safety_ratings
                try:
                    safety_ratings = getattr(candidate, 'safety_ratings', None)
                    if safety_ratings is not None:
                        candidate_meta['safety_ratings'] = [str(r) for r in safety_ratings] if hasattr(safety_ratings, '__iter__') else None
                except Exception:
                    candidate_meta['safety_ratings'] = None

                metadata['candidate'] = candidate_meta

        except Exception as e:
            metadata['extraction_error'] = str(e)

        return metadata

    def _log_api_call(self, data):
        """Save API call data to JSON log file"""
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = self.log_dir / f"image_api_calls_{timestamp}.jsonl"

        # Append to JSONL file (one JSON object per line)
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')

    def generate_from_text_and_image(self, prompt: str, base_image: Image.Image) -> Image.Image:
        """
        Generate an image by editing a base image with a text prompt.

        Args:
            prompt: Text description of the edits to make
            base_image: PIL Image to edit

        Returns:
            PIL Image object with edits applied
        """
        response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt, base_image]
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image = Image.open(BytesIO(part.inline_data.data))
                return image

        raise ValueError("No image data found in response")

    def save_image(self, image: Image.Image, filepath: str = None) -> str:
        """
        Save PIL Image to file.

        Args:
            image: PIL Image object
            filepath: Optional path where image should be saved.
                     If None, saves to default output directory with timestamp.

        Returns:
            Path to saved file
        """
        if filepath is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = self.output_dir / f"generated_image_{timestamp}.png"

        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        image.save(filepath)
        return str(filepath)

    def generate_and_save(self, prompt: str, output_path: str, log_call=True) -> str:
        """
        Generate image from prompt and save to file.

        Args:
            prompt: Text description of the image
            output_path: Path where image should be saved
            log_call: Whether to log API call data (default: True)

        Returns:
            Path to saved file
        """
        image = self.generate_from_text(prompt, log_call=log_call)
        saved_path = self.save_image(image, output_path)

        # Update log with file information
        if log_call:
            self._update_last_log_with_file(saved_path)

        return saved_path

    def _update_last_log_with_file(self, file_path):
        """Update the most recent log entry with file information"""
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = self.log_dir / f"image_api_calls_{timestamp}.jsonl"

        if not log_file.exists():
            return

        try:
            # Read all lines
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if not lines:
                return

            # Update last line with file info
            last_entry = json.loads(lines[-1])
            file_path_obj = Path(file_path)

            last_entry['saved_file'] = {
                'path': str(file_path),
                'filename': file_path_obj.name,
                'file_size_bytes': file_path_obj.stat().st_size if file_path_obj.exists() else None,
                'file_size_kb': round(file_path_obj.stat().st_size / 1024, 2) if file_path_obj.exists() else None
            }

            # Write back all lines
            with open(log_file, 'w', encoding='utf-8') as f:
                for line in lines[:-1]:
                    f.write(line)
                f.write(json.dumps(last_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            # Don't fail if logging fails
            print(f"Warning: Could not update log with file info: {e}")

