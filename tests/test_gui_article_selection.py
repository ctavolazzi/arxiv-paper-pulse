import pytest
import tkinter as tk
from unittest.mock import MagicMock, patch

from arxiv_paper_pulse.gui import ArticleSelectionDialog

@pytest.fixture
def mock_paper_data():
    """Generate mock paper data for testing."""
    return [
        {
            "entry_id": "2401.01234",
            "title": "Test Paper 1: Neural Network Optimization",
            "published": "2023-01-01T00:00:00Z",
            "url": "http://arxiv.org/abs/2401.01234",
            "abstract": "This is a test abstract for paper 1",
            "query": "test query",
            "id": "unique_id_1"
        },
        {
            "entry_id": "2401.56789",
            "title": "Test Paper 2: Advanced AI Methods",
            "published": "2023-01-02T00:00:00Z",
            "url": "http://arxiv.org/abs/2401.56789",
            "abstract": "This is a test abstract for paper 2",
            "query": "test query",
            "id": "unique_id_2"
        },
        {
            "entry_id": "2401.12345",
            "title": "Test Paper 3: Deep Learning Applications",
            "published": "2023-01-03T00:00:00Z",
            "url": "http://arxiv.org/abs/2401.12345",
            "abstract": "This is a test abstract for paper 3",
            "query": "test query",
            "id": "unique_id_3"
        }
    ]

@pytest.mark.gui
def test_article_selection_dialog_creation(mock_paper_data):
    """Test that the ArticleSelectionDialog is created correctly."""
    try:
        root = tk.Tk()
        # Use the fixture directly
        dialog = ArticleSelectionDialog(root, mock_paper_data)

        # Verify the dialog has the expected widgets and components
        assert dialog.title() == "Select Articles to Summarize"
        assert len(dialog.vars) == len(mock_paper_data)

        # All checkboxes should be selected by default
        assert all(var.get() == 1 for var in dialog.vars)

        # Clean up
        dialog.destroy()
        root.destroy()
    except tk.TclError:
        pytest.skip("Cannot run GUI tests in this environment")

@pytest.mark.gui
def test_article_selection_dialog_select_all(mock_paper_data):
    """Test the select_all function."""
    try:
        root = tk.Tk()
        dialog = ArticleSelectionDialog(root, mock_paper_data)

        # First, deselect all
        for var in dialog.vars:
            var.set(0)

        # Verify all are deselected
        assert all(var.get() == 0 for var in dialog.vars)

        # Call select_all
        dialog.select_all()

        # Verify all are selected
        assert all(var.get() == 1 for var in dialog.vars)

        # Clean up
        dialog.destroy()
        root.destroy()
    except tk.TclError:
        pytest.skip("Cannot run GUI tests in this environment")

@pytest.mark.gui
def test_article_selection_dialog_select_none(mock_paper_data):
    """Test the select_none function."""
    try:
        root = tk.Tk()
        dialog = ArticleSelectionDialog(root, mock_paper_data)

        # Verify all are selected by default
        assert all(var.get() == 1 for var in dialog.vars)

        # Call select_none
        dialog.select_none()

        # Verify all are deselected
        assert all(var.get() == 0 for var in dialog.vars)

        # Clean up
        dialog.destroy()
        root.destroy()
    except tk.TclError:
        pytest.skip("Cannot run GUI tests in this environment")

@pytest.mark.gui
def test_article_selection_dialog_ok(mock_paper_data):
    """Test the OK button functionality."""
    try:
        root = tk.Tk()
        dialog = ArticleSelectionDialog(root, mock_paper_data)

        # Deselect the middle paper (index 1)
        dialog.vars[1].set(0)

        # Mock the destroy method to prevent actual window destruction
        original_destroy = dialog.destroy
        dialog.destroy = MagicMock()

        # Call the OK method
        dialog.ok()

        # Check that destroy was called
        dialog.destroy.assert_called_once()

        # Check the selected indices and result
        assert dialog.selected_indices == [0, 2]  # Papers 1 and 3 (0-indexed)
        assert len(dialog.result) == 2
        assert dialog.result[0]["id"] == "unique_id_1"
        assert dialog.result[1]["id"] == "unique_id_3"

        # Restore original destroy and clean up
        dialog.destroy = original_destroy
        dialog.destroy()
        root.destroy()
    except tk.TclError:
        pytest.skip("Cannot run GUI tests in this environment")

@pytest.mark.gui
def test_article_selection_dialog_cancel(mock_paper_data):
    """Test the cancel button functionality."""
    try:
        root = tk.Tk()
        dialog = ArticleSelectionDialog(root, mock_paper_data)

        # Mock the destroy method to prevent actual window destruction
        original_destroy = dialog.destroy
        dialog.destroy = MagicMock()

        # Call the cancel method
        dialog.cancel()

        # Check that destroy was called
        dialog.destroy.assert_called_once()

        # Check that result is None
        assert dialog.result is None

        # Restore original destroy and clean up
        dialog.destroy = original_destroy
        dialog.destroy()
        root.destroy()
    except tk.TclError:
        pytest.skip("Cannot run GUI tests in this environment")

@pytest.mark.gui
@patch('tkinter.Toplevel')
@patch('tkinter.Frame')
@patch('tkinter.Label')
@patch('tkinter.Checkbutton')
@patch('tkinter.Button')
@patch('tkinter.Canvas')
@patch('tkinter.Scrollbar')
def test_article_selection_dialog_mocked(mock_scrollbar, mock_canvas, mock_button,
                                       mock_checkbutton, mock_label, mock_frame,
                                       mock_toplevel, mock_paper_data):
    """Test the ArticleSelectionDialog with mocked Tkinter components."""
    # This test uses mocks to avoid actual GUI creation, making it runnable in headless environments

    root = MagicMock()

    # Setup mock returns
    mock_frame_instance = MagicMock()
    mock_frame.return_value = mock_frame_instance

    # Create the dialog with mocked components
    dialog = ArticleSelectionDialog(root, mock_paper_data)

    # Test selection methods without actual GUI
    dialog.select_all()
    assert all(var.get() == 1 for var in dialog.vars)

    dialog.select_none()
    assert all(var.get() == 0 for var in dialog.vars)

    # Test OK functionality
    dialog.vars[0].set(1)  # Select first paper
    dialog.ok()
    assert dialog.selected_indices == [0]
    assert len(dialog.result) == 1
    assert dialog.result[0]["id"] == "unique_id_1"