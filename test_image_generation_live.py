#!/usr/bin/env python3
"""
Live test script for ImageGenerator - generates a real image using Gemini API
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from arxiv_paper_pulse.image_generator import ImageGenerator
from arxiv_paper_pulse import config

def main():
    print("🎨 Testing ImageGenerator with real Gemini API...")
    print(f"📁 Output directory: {config.IMAGE_OUTPUT_DIR}")
    print()

    # Check if API key is configured
    if not config.GEMINI_API_KEY:
        print("❌ Error: GEMINI_API_KEY not found in environment")
        print("   Please set it in your .env file")
        return 1

    try:
        # Initialize generator
        print("✅ Initializing ImageGenerator...")
        generator = ImageGenerator()
        print(f"   Model: {generator.model}")
        print(f"   Output dir: {generator.output_dir}")
        print()

        # Generate a simple test image
        test_prompt = "A minimalist illustration of a colorful geometric shape on a white background"
        print(f"🖼️  Generating image from prompt:")
        print(f'   "{test_prompt}"')
        print("   This may take a few seconds...")
        print()

        image = generator.generate_from_text(test_prompt)
        print(f"✅ Image generated successfully!")
        print(f"   Size: {image.size[0]}x{image.size[1]} pixels")
        print(f"   Mode: {image.mode}")
        print()

        # Save the image
        print("💾 Saving image...")
        saved_path = generator.save_image(image)
        print(f"✅ Image saved to: {saved_path}")
        print()

        # Verify file exists
        image_path = Path(saved_path)
        if image_path.exists():
            file_size = image_path.stat().st_size
            print(f"✅ File verified:")
            print(f"   Path: {saved_path}")
            print(f"   Size: {file_size:,} bytes ({file_size / 1024:.2f} KB)")
            print()
            print("🎉 Success! Image generation is working correctly!")
            print(f"📂 Check the generated_images folder: {generator.output_dir}")
            return 0
        else:
            print(f"❌ Error: File not found at {saved_path}")
            return 1

    except Exception as e:
        print(f"❌ Error during image generation: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

