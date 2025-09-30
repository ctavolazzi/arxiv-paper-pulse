import tkinter as tk
import threading
import time
import pytest
from arxiv_paper_pulse.gui import create_gui, run_crawl, check_total

@pytest.mark.integration
def test_run_crawl_integration(monkeypatch):
    """
    Integration test for the GUI crawl functionality that uses the actual network and model calls.
    To avoid thread issues (and to force synchronous execution so we can inspect widget output),
    we monkey‑patch threading.Thread so that it runs the target immediately on the main thread.
    """
    # Create the GUI instance.
    root, query_entry, max_results_entry, output_area, status_label, model_var, recent_days_var = create_gui()

    # Set up entries to use a known query that should return a small number of results.
    query_entry.delete(0, tk.END)
    query_entry.insert(0, "cat:cs.AI")
    max_results_entry.delete(0, tk.END)
    max_results_entry.insert(0, "1")
    recent_days_var.set("7")

    # Monkey-patch threading.Thread to run synchronously on the main thread.
    def fake_thread(target, **kwargs):
        target()
        class DummyThread:
            def start(self):
                pass
        return DummyThread()
    monkeypatch.setattr(threading, "Thread", fake_thread)

    # Run the crawl function.
    run_crawl(query_entry.get(), int(max_results_entry.get()), model_var.get(), int(recent_days_var.get()), output_area, status_label)

    # Allow the GUI to process any pending updates.
    root.update_idletasks()
    root.update()

    # Get the contents of the output area.
    content = output_area.get("1.0", tk.END)
    # We expect that a paper summary has been inserted.
    assert "Summarizing paper" in content, "Output area did not contain expected crawl output."

    root.destroy()

@pytest.mark.integration
def test_check_total_integration(monkeypatch):
    """
    Integration test for the check_total function.
    This test uses the real pagination and date filtering logic (which makes network requests).
    We capture the messagebox output to inspect the total.
    """
    messages = []
    def fake_showinfo(title, message):
        messages.append((title, message))
    monkeypatch.setattr("arxiv_paper_pulse.gui.messagebox.showinfo", fake_showinfo)

    # Prevent any warning dialogs from blocking the test.
    monkeypatch.setattr("arxiv_paper_pulse.gui.messagebox.askyesno", lambda title, msg: True)

    # Call check_total with a live query.
    check_total("cat:cs.AI", 7)

    # We don't know the exact number in live data; simply ensure a message was produced.
    assert len(messages) == 1, "No message was shown by check_total integration test."
    # Optionally, print the message for manual inspection.
    print("Integration check_total message:", messages[0][1])
