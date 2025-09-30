import pytest
import re
from arxiv_paper_pulse import config
from arxiv_paper_pulse.core import ArxivSummarizer

def test_summary_prompt_format():
    """Test that the summary prompt is correctly formatted."""
    # Check that the prompt contains all the required sections
    assert "Key Problem & Research Question" in config.SUMMARY_PROMPT
    assert "Methodology & Approach" in config.SUMMARY_PROMPT
    assert "Main Findings & Contributions" in config.SUMMARY_PROMPT
    assert "Implications & Significance" in config.SUMMARY_PROMPT
    assert "Limitations & Future Directions" in config.SUMMARY_PROMPT

    # Check that the prompt has placeholders for the paper abstract
    assert "{}" in config.SUMMARY_PROMPT

def test_synthesis_prompt_format():
    """Test that the synthesis prompt is correctly formatted."""
    # Check that the prompt contains all the required elements
    assert "most significant insights" in config.SYNTHESIS_PROMPT
    assert "emerging trends" in config.SYNTHESIS_PROMPT
    assert "real-world implications" in config.SYNTHESIS_PROMPT
    assert "actionable takeaways" in config.SYNTHESIS_PROMPT

    # Check that the prompt has formatting instructions
    assert "executive summary" in config.SYNTHESIS_PROMPT.lower()
    assert "bullet points" in config.SYNTHESIS_PROMPT

    # Check that the prompt has placeholders for the article summaries
    assert "{}" in config.SYNTHESIS_PROMPT

def test_ollama_summarize_uses_correct_prompt(monkeypatch):
    """Test that the ollama_summarize method uses the correct prompt from config."""
    # Create a mock subprocess.run that captures the prompt
    captured_prompt = None

    def mock_subprocess_run(args, **kwargs):
        nonlocal captured_prompt
        # Handle both ollama list and ollama run commands
        if args[0] == "ollama":
            if args[1] == "list":
                # Mock the list of installed models
                return type('CompletedProcess', (), {
                    'returncode': 0,
                    'stdout': "NAME        	ID    	SIZE  	MODIFIED\nllama2      	latest	3.8 GB	7 hours ago\n",
                    'stderr': ""
                })
            elif args[1] == "run" and len(args) > 2:
                # Capture the prompt from ollama run command
                captured_prompt = args[2]

        return type('CompletedProcess', (), {
            'returncode': 0,
            'stdout': "Mocked summary output",
            'stderr': ""
        })

    # Apply the mock
    monkeypatch.setattr("subprocess.run", mock_subprocess_run)

    # Create a summarizer and call ollama_summarize
    summarizer = ArxivSummarizer()
    test_abstract = "This is a test abstract."
    summary = summarizer.ollama_summarize(test_abstract)

    # Check that the correct prompt from config was used
    expected_prompt = config.SUMMARY_PROMPT.format(test_abstract)
    assert captured_prompt == expected_prompt

def test_summary_prompt_think_tokens():
    """Test that the summary prompt includes think tokens for better reasoning."""
    assert "<think>" in config.SUMMARY_PROMPT
    assert "</think>" in config.SUMMARY_PROMPT

def test_paper_abstract_placement():
    """Test that the paper abstract is placed at the end of the prompt."""
    # The abstract placeholder should be after all prompt instructions
    prompt_parts = config.SUMMARY_PROMPT.split("{}")
    assert len(prompt_parts) == 2

    # Check that key instructions are in the first part (before the abstract)
    first_part = prompt_parts[0]
    assert "Key Problem & Research Question" in first_part
    assert "Implications & Significance" in first_part

    # The second part should be mostly empty (just formatting, if anything)
    second_part = prompt_parts[1].strip()
    assert len(second_part) <= 5  # Allow for some whitespace or formatting

def test_implications_section_emphasis():
    """Test that the Implications & Significance section is properly emphasized."""
    # Extract the Implications section using regex
    implications_section = re.search(r"4\.\s+Implications & Significance:.*?5\.",
                                     config.SUMMARY_PROMPT, re.DOTALL)
    assert implications_section, "Implications section not found"

    implications_text = implications_section.group(0)

    # Check for specific questions about implications
    assert "mean for the field or industry" in implications_text
    assert "practical applications" in implications_text
    assert "change our understanding" in implications_text