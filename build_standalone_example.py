#!/usr/bin/env python3
"""
Build a standalone example of the finished product step by step.
This creates a complete blog post about an arXiv article WITHOUT using the app.
"""
import arxiv
from pathlib import Path
from datetime import datetime
from google import genai
import os

from arxiv_paper_pulse.documents import DocumentProcessor, DocumentInput, DocumentFromURL, DocumentProcessingConfig, OutputFormat
from arxiv_paper_pulse.image_generator import ImageGenerator
from arxiv_paper_pulse import config


def fetch_arxiv_paper(paper_id: str):
    """Step 1: Fetch paper metadata from arXiv."""
    print(f"📄 Step 1: Fetching arXiv paper {paper_id}...")
    search = arxiv.Search(id_list=[paper_id])
    client = arxiv.Client()
    results = list(client.results(search))

    if not results:
        raise ValueError(f"Paper {paper_id} not found")

    paper = results[0]
    metadata = {
        'paper_id': paper_id,
        'title': paper.title,
        'authors': [author.name for author in paper.authors],
        'published': str(paper.published),
        'abstract': paper.summary,
        'arxiv_url': paper.entry_id,
        'pdf_url': paper.pdf_url,
    }

    print(f"   ✅ Fetched: {metadata['title']}")
    print(f"   Authors: {', '.join(metadata['authors'][:3])}...")
    return metadata


def analyze_paper(pdf_url: str):
    """Step 2: Analyze the paper PDF."""
    print(f"🔍 Step 2: Analyzing paper PDF...")

    doc_processor = DocumentProcessor()
    doc_input = DocumentInput(source=DocumentFromURL(url=pdf_url))
    doc_config = DocumentProcessingConfig(
        prompt="""Analyze this research paper comprehensively. Provide a detailed analysis covering:
1. Problem statement and significance
2. Methodology and approach
3. Key findings and contributions
4. Implications and applications
5. Limitations and future directions

Focus on clarity and depth. Extract key concepts that could be visualized.""",
        output_format=OutputFormat.TEXT
    )

    result = doc_processor.process(doc_input, doc_config)
    if not result.success:
        raise ValueError(f"Analysis failed: {result.error}")

    print(f"   ✅ Analysis complete ({len(result.text)} characters)")
    return result.text


def generate_image_prompt(analysis_text: str, metadata: dict):
    """Step 3: Generate image prompt from analysis."""
    print(f"🖼️  Step 3: Generating image prompt...")

    client = genai.Client(api_key=config.GEMINI_API_KEY)

    prompt = f"""You are an expert at creating visual prompts for AI image generation. Your task is to create a prompt that generates an image which VISUALLY EXPLAINS the research paper like a scientific infographic or educational diagram.

CRITICAL REQUIREMENTS - The image must be EXPLANATORY:
1. The image should function like a visual summary that helps readers understand the research
2. Include recognizable visual elements: diagrams, flow charts, labeled components, icons, or illustrations
3. Show the actual WORKFLOW or PROCESS described in the paper (e.g., "input → processing → output")
4. Use text labels or annotations when helpful to explain concepts
5. Think like a scientific illustrator creating a figure for a research paper
6. Avoid abstract art - make it concrete and educational
7. Someone should be able to look at the image and understand what the research does

Paper Title: {metadata['title']}
Abstract: {metadata['abstract']}

Paper Analysis:
{analysis_text[:2000]}

STEP 1: Analyze the paper and extract:
- What is the main system/technology?
- What does it do?
- What are the key components?
- What are concrete metrics or numbers mentioned?
- What are the outputs or results?

STEP 2: Create a visual explanation that includes:
- A clear central element representing the main system (labeled if needed)
- Visual arrows or flows showing how it works
- Iconic representations of inputs
- Visual representation of the processing
- Output visualization
- Icons or symbols representing the scientific fields mentioned
- Visual elements showing scale

STEP 3: Write the prompt with SPECIFIC visual elements:
- Describe the layout: "Left side shows inputs, center shows the system, right side shows outputs"
- Use specific visual metaphors
- Include labels/text: "Small text labels on key elements", "Annotated diagrams"
- Specify icons
- Show relationships: "Connected nodes", "Flowing pathways", "Converging streams"

Style: Professional scientific infographic style, like Nature or Science magazine figures. Clean, modern, educational. Use a color palette that's professional but visually appealing. Include both illustrations and diagrammatic elements.

Layout: 16:9 aspect ratio, wide format suitable for blog hero. Use rule of thirds or centered composition. Left-to-right flow showing the process.

Return ONLY the image prompt text. Be very specific about what visual elements should appear and how they explain the research. Length: 400-500 words."""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt]
    )

    image_prompt = response.text.strip()
    print(f"   ✅ Image prompt generated ({len(image_prompt)} characters)")
    return image_prompt


def generate_featured_image(image_prompt: str, paper_id: str):
    """Step 4: Generate featured image."""
    print(f"🎨 Step 4: Generating featured image...")

    img_generator = ImageGenerator()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_filename = f"example_hero_{paper_id}_{timestamp}.png"
    image_path = Path(config.IMAGE_OUTPUT_DIR) / image_filename

    saved_path = img_generator.generate_and_save(
        image_prompt,
        str(image_path)
    )

    print(f"   ✅ Image saved: {saved_path}")
    return saved_path


def generate_blog_post(metadata: dict, analysis_text: str):
    """Step 5: Generate blog post content."""
    print(f"✍️  Step 5: Generating blog post...")

    client = genai.Client(api_key=config.GEMINI_API_KEY)

    article_prompt = f"""Write a comprehensive, accessible blog post about this research paper.

Paper Title: {metadata['title']}
Authors: {', '.join(metadata['authors'])}
Published: {metadata['published']}
arXiv ID: {metadata['paper_id']}
Abstract: {metadata['abstract']}

Paper Analysis:
{analysis_text}

Write an article with the following structure:
1. Title (use the paper title)
2. Introduction - Context and motivation for the research, written in an engaging way
3. What This Research Does - Clear explanation of the problem and approach
4. Key Findings - Detailed breakdown of the methodology, findings, and contributions
5. Why This Matters - Implications, applications, and significance
6. Technical Deep Dive - More detailed technical discussion for interested readers
7. Conclusion - Summary of key takeaways
8. References - Link to original paper and PDF

Write in a clear, accessible style suitable for readers interested in research but not necessarily experts in the field. Use engaging language and explain technical concepts clearly. Make it blog-post style, not academic style."""

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=[article_prompt]
    )

    blog_content = response.text
    print(f"   ✅ Blog post generated ({len(blog_content)} characters)")
    return blog_content


def build_html_page(metadata: dict, blog_content: str, image_path: str, analysis_text: str):
    """Step 6: Build the HTML page."""
    print(f"🌐 Step 6: Building HTML page...")

    # Convert markdown-style content to HTML
    import markdown
    html_body = markdown.markdown(blog_content, extensions=['extra', 'codehilite'])

    # Build full HTML page
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{metadata['title']} - ArXiv Paper Blog</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Crimson+Text:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #2563eb;
            --primary-dark: #1e40af;
            --secondary: #7c3aed;
            --text: #1f2937;
            --text-light: #6b7280;
            --bg: #ffffff;
            --bg-light: #f9fafb;
            --border: #e5e7eb;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Crimson Text', serif;
            line-height: 1.8;
            color: var(--text);
            background: var(--bg-light);
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: var(--bg);
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}

        header {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: white;
            padding: 60px 40px;
            text-align: center;
        }}

        header h1 {{
            font-family: 'Inter', sans-serif;
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 20px;
            line-height: 1.2;
        }}

        .hero-image-container {{
            position: relative;
            width: 100%;
            margin: 0;
            overflow: hidden;
        }}

        .hero-image {{
            width: 100%;
            height: auto;
            aspect-ratio: 16 / 9;
            object-fit: cover;
            display: block;
            cursor: pointer;
            transition: transform 0.3s ease;
        }}

        .hero-image:hover {{
            transform: scale(1.02);
        }}

        .hero-image-overlay {{
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            background: linear-gradient(to top, rgba(0,0,0,0.8), transparent);
            color: white;
            padding: 40px;
            font-family: 'Inter', sans-serif;
        }}

        .hero-image-overlay h2 {{
            font-size: 1.8rem;
            font-weight: 600;
            margin: 0;
        }}

        .metadata {{
            background: var(--bg-light);
            padding: 30px 40px;
            border-bottom: 1px solid var(--border);
        }}

        .metadata-item {{
            margin: 10px 0;
            font-size: 0.95rem;
        }}

        .metadata-item strong {{
            color: var(--primary);
            font-family: 'Inter', sans-serif;
            font-weight: 600;
        }}

        .metadata-links {{
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid var(--border);
        }}

        .metadata-links a {{
            display: inline-block;
            margin-right: 20px;
            margin-bottom: 10px;
            padding: 10px 20px;
            background: var(--primary);
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-family: 'Inter', sans-serif;
            font-weight: 500;
            transition: background 0.2s;
        }}

        .metadata-links a:hover {{
            background: var(--primary-dark);
        }}

        .content {{
            padding: 50px 40px;
        }}

        .content h1, .content h2, .content h3 {{
            font-family: 'Inter', sans-serif;
            color: var(--text);
            margin-top: 40px;
            margin-bottom: 20px;
        }}

        .content h1 {{
            font-size: 2.2rem;
            border-bottom: 3px solid var(--primary);
            padding-bottom: 10px;
        }}

        .content h2 {{
            font-size: 1.8rem;
            color: var(--primary);
        }}

        .content h3 {{
            font-size: 1.4rem;
        }}

        .content p {{
            margin: 20px 0;
            font-size: 1.1rem;
        }}

        .content ul, .content ol {{
            margin: 20px 0;
            padding-left: 30px;
        }}

        .content li {{
            margin: 10px 0;
        }}

        .content code {{
            background: var(--bg-light);
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}

        .content pre {{
            background: var(--bg-light);
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 20px 0;
        }}

        .original-abstract {{
            background: var(--bg-light);
            padding: 30px;
            border-left: 4px solid var(--primary);
            margin: 40px 0;
            border-radius: 4px;
        }}

        .original-abstract h3 {{
            margin-top: 0;
            color: var(--primary);
        }}

        footer {{
            background: var(--bg-light);
            padding: 30px 40px;
            text-align: center;
            border-top: 1px solid var(--border);
            color: var(--text-light);
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{metadata['title']}</h1>
        </header>

        <div class="hero-image-container">
            <img src="{Path(image_path).name}" alt="Visual explanation of {metadata['title']}" class="hero-image" onclick="window.open(this.src, '_blank')">
            <div class="hero-image-overlay">
                <h2>An AI-generated visual explanation of this research</h2>
            </div>
        </div>

        <div class="metadata">
            <div class="metadata-item">
                <strong>Authors:</strong> {', '.join(metadata['authors'])}
            </div>
            <div class="metadata-item">
                <strong>Published:</strong> {metadata['published']}
            </div>
            <div class="metadata-item">
                <strong>arXiv ID:</strong> {metadata['paper_id']}
            </div>
            <div class="metadata-links">
                <a href="{metadata['arxiv_url']}" target="_blank">📄 View on arXiv</a>
                <a href="{metadata['pdf_url']}" target="_blank">📥 Download PDF</a>
            </div>
        </div>

        <div class="content">
            {html_body}

            <div class="original-abstract">
                <h3>Original Abstract from arXiv</h3>
                <p>{metadata['abstract']}</p>
            </div>
        </div>

        <footer>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | ArXiv Paper Pulse</p>
        </footer>
    </div>
</body>
</html>"""

    # Save HTML file
    output_dir = Path("example_output")
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_file = output_dir / f"example_blog_{metadata['paper_id']}_{timestamp}.html"
    html_file.write_text(html_content, encoding='utf-8')

    # Copy image to output directory
    import shutil
    image_dest = output_dir / Path(image_path).name
    shutil.copy(image_path, image_dest)

    print(f"   ✅ HTML page saved: {html_file}")
    print(f"   ✅ Image copied to: {image_dest}")

    return str(html_file)


def main():
    """Main function to build the standalone example."""
    # Use the Kosmos paper as example
    paper_id = "2511.02824"
    paper_url = f"https://arxiv.org/abs/{paper_id}"

    print("=" * 80)
    print("BUILDING STANDALONE EXAMPLE - STEP BY STEP")
    print("=" * 80)
    print()
    print(f"Paper: {paper_url}")
    print()

    try:
        # Step 1: Fetch paper
        metadata = fetch_arxiv_paper(paper_id)
        print()

        # Step 2: Analyze paper
        pdf_url = f"https://arxiv.org/pdf/{paper_id}"
        analysis_text = analyze_paper(pdf_url)
        print()

        # Step 3: Generate image prompt
        image_prompt = generate_image_prompt(analysis_text, metadata)
        print()

        # Step 4: Generate featured image
        image_path = generate_featured_image(image_prompt, paper_id)
        print()

        # Step 5: Generate blog post
        blog_content = generate_blog_post(metadata, analysis_text)
        print()

        # Step 6: Build HTML page
        html_file = build_html_page(metadata, blog_content, image_path, analysis_text)
        print()

        print("=" * 80)
        print("✅ STANDALONE EXAMPLE COMPLETE")
        print("=" * 80)
        print(f"📄 HTML File: {html_file}")
        print(f"🖼️  Image: {Path(image_path).name}")
        print()
        print("Open the HTML file in your browser to view the example!")

        return html_file

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()

