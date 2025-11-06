#!/usr/bin/env python3
"""
Generate an image prompt from an article abstract using Gemini API.
Specifically designed for creating blog hero images (16:9 aspect ratio).
"""
import sys
from pathlib import Path
from google import genai
from arxiv_paper_pulse import config


def extract_abstract_from_article(article_path: str) -> str:
    """Extract abstract section from markdown article."""
    article_file = Path(article_path)
    if not article_file.exists():
        raise FileNotFoundError(f"Article file not found: {article_path}")

    content = article_file.read_text(encoding='utf-8')

    # Find abstract section
    lines = content.split('\n')
    abstract_start = None
    abstract_end = None

    for i, line in enumerate(lines):
        if line.strip().lower().startswith('### abstract') or line.strip().lower().startswith('## abstract'):
            abstract_start = i + 1
            break

    if abstract_start is None:
        # Try to find it in the content text
        for i, line in enumerate(lines):
            if 'abstract' in line.lower() and 'kosmos' in line.lower():
                # Look for the paragraph after this
                abstract_start = i
                break

    if abstract_start is None:
        raise ValueError("Could not find abstract section in article")

    # Find where abstract ends (next heading or section)
    abstract_lines = []
    for i in range(abstract_start, len(lines)):
        line = lines[i]
        # Stop at next heading or section divider
        if line.strip().startswith('##') or line.strip().startswith('###') or line.strip().startswith('---'):
            break
        if line.strip():
            abstract_lines.append(line.strip())

    abstract = ' '.join(abstract_lines)
    return abstract


def generate_image_prompt_from_abstract(abstract: str, model: str = "gemini-2.5-flash") -> str:
    """
    Generate a detailed image prompt from an article abstract using Gemini.

    Args:
        abstract: The article abstract text
        model: Gemini model to use (default: gemini-2.5-flash)

    Returns:
        A detailed image prompt optimized for blog hero images
    """
    if not config.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set in environment")

    client = genai.Client(api_key=config.GEMINI_API_KEY)

    prompt = f"""You are an expert at creating visual prompts for AI image generation. Your task is to create a prompt that generates an image which VISUALLY EXPLAINS the abstract like a scientific infographic or educational diagram.

CRITICAL REQUIREMENTS - The image must be EXPLANATORY:
1. The image should function like a visual summary that helps readers understand the abstract
2. Include recognizable visual elements: diagrams, flow charts, labeled components, icons, or illustrations
3. Show the actual WORKFLOW or PROCESS described in the abstract (e.g., "input → processing → output")
4. Use text labels or annotations when helpful to explain concepts
5. Think like a scientific illustrator creating a figure for a research paper
6. Avoid abstract art - make it concrete and educational
7. Someone should be able to look at the image and understand what the research does

Abstract:
{abstract}

STEP 1: Analyze the abstract and extract:
- What is the main system/technology? (e.g., "Kosmos AI system")
- What does it do? (e.g., "automates scientific discovery", "analyzes data and searches literature")
- What are the key components? (e.g., "structured world model", "data analysis agent", "literature search agent")
- What are concrete metrics or numbers mentioned? (e.g., "42,000 lines of code", "1,500 papers", "7 discoveries")
- What are the outputs or results? (e.g., "scientific reports", "novel discoveries")

STEP 2: Create a visual explanation that includes:
- A clear central element representing the main system (labeled if needed)
- Visual arrows or flows showing how it works
- Iconic representations of inputs (e.g., datasets, research papers)
- Visual representation of the processing (e.g., code blocks, analysis charts)
- Output visualization (e.g., reports, discoveries, findings)
- Icons or symbols representing the scientific fields mentioned
- Visual elements showing scale (e.g., stacks of papers, code lines, data points)

STEP 3: Write the prompt with SPECIFIC visual elements:
- Describe the layout: "Left side shows inputs, center shows the system, right side shows outputs"
- Use specific visual metaphors: "A central hexagonal node labeled 'Kosmos World Model'", "Data streams flowing in", "Code blocks being processed", "Papers being analyzed"
- Include labels/text: "Small text labels on key elements", "Annotated diagrams"
- Specify icons: "DNA helix icon for genetics", "Microscope icon for biology", "Code brackets icon for data analysis"
- Show relationships: "Connected nodes", "Flowing pathways", "Converging streams"

Style: Professional scientific infographic style, like Nature or Science magazine figures. Clean, modern, educational. Use a color palette that's professional but visually appealing. Include both illustrations and diagrammatic elements.

Layout: 16:9 aspect ratio, wide format suitable for blog hero. Use rule of thirds or centered composition. Left-to-right flow showing the process.

Return ONLY the image prompt text. Be very specific about what visual elements should appear and how they explain the abstract. Length: 400-500 words. Make it so detailed that the resulting image clearly explains the abstract to someone who hasn't read it."""

    response = client.models.generate_content(
        model=model,
        contents=[prompt]
    )

    return response.text.strip()


def main():
    """Main function to generate image prompt from article."""
    if len(sys.argv) < 2:
        print("Usage: python generate_article_image_prompt.py <article_path>")
        print("Example: python generate_article_image_prompt.py arxiv_paper_pulse/data/articles/article_2511.02824_20251104_204421.md")
        sys.exit(1)

    article_path = sys.argv[1]

    print("=" * 80)
    print("📝 Article Abstract to Image Prompt Generator")
    print("=" * 80)
    print()
    print(f"📄 Article: {article_path}")
    print()

    try:
        # Extract abstract
        print("Step 1: Extracting abstract from article...")
        abstract = extract_abstract_from_article(article_path)
        print(f"   ✅ Abstract extracted ({len(abstract)} characters)")
        print()
        print("Abstract preview:")
        print("-" * 80)
        print(abstract[:300] + "..." if len(abstract) > 300 else abstract)
        print("-" * 80)
        print()

        # Generate image prompt
        print("Step 2: Generating image prompt using Gemini...")
        image_prompt = generate_image_prompt_from_abstract(abstract)
        print(f"   ✅ Image prompt generated ({len(image_prompt)} characters)")
        print()

        # Display prompt
        print("=" * 80)
        print("🎨 Generated Image Prompt")
        print("=" * 80)
        print()
        print(image_prompt)
        print()

        # Save prompt
        article_file = Path(article_path)
        prompt_file = article_file.parent / f"{article_file.stem}_image_prompt.txt"
        prompt_file.write_text(image_prompt, encoding='utf-8')
        print(f"💾 Prompt saved to: {prompt_file}")
        print()

        return image_prompt

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

