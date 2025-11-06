#!/usr/bin/env python3
"""
Generate multiple test images with different prompts to showcase ImageGenerator capabilities
"""

import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from arxiv_paper_pulse.image_generator import ImageGenerator
from arxiv_paper_pulse import config

PROMPTS = [
    # Simple & Clean
    "A minimalist illustration of a colorful geometric shape on a white background",

    # Photorealistic
    "A photorealistic close-up portrait of an elderly Japanese ceramicist with deep, sun-etched wrinkles inspecting a freshly glazed tea bowl. The setting is a rustic, sun-drenched workshop. Soft, golden hour light streaming through a window.",

    # Stylized/Sticker
    "A kawaii-style sticker of a happy red panda wearing a tiny bamboo hat. It's munching on a green bamboo leaf. The design features bold, clean outlines, simple cel-shading, and a vibrant color palette. White background.",

    # Text/Logo
    "Create a modern, minimalist logo for a coffee shop called 'The Daily Grind'. The text should be in a clean, bold, sans-serif font. The design features a simple, stylized icon of a coffee bean integrated with the text. Black and white color scheme.",

    # Product Mockup
    "A high-resolution, studio-lit product photograph of a minimalist ceramic coffee mug in matte black, presented on a polished concrete surface. The lighting is a three-point softbox setup. The camera angle is a slightly elevated 45-degree shot. Ultra-realistic, with sharp focus on the steam rising from the coffee. Square image.",

    # Minimalist/Negative Space
    "A minimalist composition featuring a single, delicate red maple leaf positioned in the bottom-right of the frame. The background is a vast, empty off-white canvas, creating significant negative space for text. Soft, diffused lighting from the top left. Square image.",

    # Comic/Illustration
    "A single comic book panel in a gritty, noir art style with high-contrast black and white inks. In the foreground, a detective in a trench coat stands under a flickering streetlamp, rain soaking his shoulders. A caption box reads 'The city was a tough place to keep secrets.' Landscape orientation.",

    # Abstract/Artistic
    "An abstract digital art composition featuring flowing, organic shapes in vibrant blues, purples, and gold. The composition suggests movement and energy. Modern, sleek aesthetic with subtle gradients and soft lighting.",

    # Game Asset Style
    "A fantasy game card illustration featuring an ornate elven plate armor set, etched with silver leaf patterns. The armor has a high collar and pauldrons shaped like falcon wings. Dramatic lighting against a mystical forest background. Vertical card format.",

    # Scientific/Technical
    "A clean, technical diagram style illustration of a neural network architecture. Nodes connected by lines, labeled with mathematical notation. Modern, minimalist design with subtle color coding. White background with blue and gray accents."
]

def main():
    print("🎨 Testing ImageGenerator with Multiple Prompts...")
    print(f"📁 Output directory: {config.IMAGE_OUTPUT_DIR}")
    print(f"🖼️  Generating {len(PROMPTS)} different images...")
    print("=" * 70)
    print()

    if not config.GEMINI_API_KEY:
        print("❌ Error: GEMINI_API_KEY not found in environment")
        return 1

    try:
        generator = ImageGenerator()
        generated_images = []
        failed_prompts = []

        for i, prompt in enumerate(PROMPTS, 1):
            print(f"[{i}/{len(PROMPTS)}] Generating image {i}...")
            print(f"   Prompt: {prompt[:60]}...")

            try:
                start_time = time.time()
                image = generator.generate_from_text(prompt)
                generation_time = time.time() - start_time

                # Save with descriptive name
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"test_image_{i:02d}_{timestamp}.png"
                output_path = generator.output_dir / filename

                saved_path = generator.save_image(image, str(output_path))

                file_size = Path(saved_path).stat().st_size

                print(f"   ✅ Success! ({generation_time:.1f}s)")
                print(f"   📄 Saved: {Path(saved_path).name}")
                print(f"   📏 Size: {image.size[0]}x{image.size[1]}px, {file_size/1024:.1f}KB")
                print()

                generated_images.append({
                    'number': i,
                    'prompt': prompt,
                    'path': saved_path,
                    'size': image.size,
                    'file_size': file_size,
                    'time': generation_time
                })

                # Small delay to avoid rate limits
                if i < len(PROMPTS):
                    time.sleep(2)

            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
                print()
                failed_prompts.append((i, prompt, str(e)))

        # Summary
        print("=" * 70)
        print("📊 GENERATION SUMMARY")
        print("=" * 70)
        print(f"✅ Successfully generated: {len(generated_images)}/{len(PROMPTS)} images")

        if failed_prompts:
            print(f"❌ Failed: {len(failed_prompts)} prompts")

        if generated_images:
            total_time = sum(img['time'] for img in generated_images)
            avg_time = total_time / len(generated_images)
            total_size = sum(img['file_size'] for img in generated_images)

            print(f"\n📈 Statistics:")
            print(f"   Total generation time: {total_time:.1f}s")
            print(f"   Average per image: {avg_time:.1f}s")
            print(f"   Total file size: {total_size/1024/1024:.2f}MB")
            print(f"\n📂 All images saved to: {generator.output_dir}")
            print("\n🎨 Generated Images:")
            for img in generated_images:
                print(f"   {img['number']:2d}. {Path(img['path']).name}")

        if failed_prompts:
            print("\n⚠️  Failed Prompts:")
            for num, prompt, error in failed_prompts:
                print(f"   {num}. {prompt[:50]}... - {error}")

        print("\n🎉 Test complete!")
        return 0

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

