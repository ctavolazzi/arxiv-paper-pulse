import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading, feedparser, urllib.parse, subprocess, datetime
from arxiv_paper_pulse.core import ArxivSummarizer
from arxiv_paper_pulse.utils import get_unique_id, parse_date, get_installed_ollama_models
from pathlib import Path
from arxiv_paper_pulse import config

# Global set to track pulled article IDs
pulled_article_ids = set()

def check_total(query, recent_days):
    """
    Paginates through results in batches (100 at a time) for the given query,
    counts how many articles have an 'updated' date within the last `recent_days` days,
    and stops once an article older than that is encountered.
    """
    # Warn if recent_days is more than 7 days
    if recent_days > 7:
        proceed = messagebox.askyesno("Warning",
            f"Using a date filter greater than 7 days may crash or freeze your computer.\n"
            f"Do you wish to proceed with a {recent_days}-day filter?")
        if not proceed:
            return

    try:
        base_url = "http://export.arxiv.org/api/query?"
        start = 0
        per_page = 100  # Batch size
        total_filtered = 0
        now = datetime.datetime.utcnow()

        while True:
            params = {
                "search_query": query,
                "start": start,
                "max_results": per_page,
                "sortBy": "submittedDate",
                "sortOrder": "descending"
            }
            url = base_url + urllib.parse.urlencode(params)
            feed = feedparser.parse(url)
            if not hasattr(feed, "entries") or not feed.entries:
                break  # No more articles

            for entry in feed.entries:
                updated_str = entry.get("updated")
                if updated_str:
                    paper_date = parse_date(updated_str)
                    if (now - paper_date).days <= recent_days:
                        total_filtered += 1
                    else:
                        messagebox.showinfo("Total Articles",
                            f"Total available articles for '{query}' in the last {recent_days} days: {total_filtered}")
                        return
            start += per_page

        messagebox.showinfo("Total Articles",
            f"Total available articles for '{query}' in the last {recent_days} days: {total_filtered}")
    except Exception as e:
        messagebox.showerror("Error", f"Error checking total articles: {e}")

def run_crawl(query, max_results, model_name, recent_days, output_area, status_label):
    def crawl_thread():
        status_label.config(text="Crawling...")
        try:
            summarizer = ArxivSummarizer(max_results=max_results, query=query, model=model_name)
            raw_data = summarizer.fetch_raw_data(force_pull=True)

            # Apply date filtering if recent_days > 0
            if recent_days > 0:
                filtered_data = []
                now = datetime.datetime.utcnow()
                for paper in raw_data:
                    updated_str = paper.get("updated")
                    if updated_str:
                        paper_date = parse_date(updated_str)
                        if (now - paper_date).days <= recent_days:
                            filtered_data.append(paper)
                raw_data = filtered_data

            # Filter out articles that have already been processed
            new_articles = []
            for paper in raw_data:
                unique_id = get_unique_id(paper)
                if unique_id and unique_id not in pulled_article_ids:
                    new_articles.append(paper)
                    pulled_article_ids.add(unique_id)

            output_area.delete("1.0", tk.END)
            total = len(new_articles)
            for i, paper in enumerate(new_articles, start=1):
                msg = f"Summarizing paper {i}/{total}: {paper['title']}\n"
                output_area.insert(tk.END, msg)
                output_area.see(tk.END)
                summary = summarizer.ollama_summarize(paper["abstract"])
                paper["summary"] = summary
                output_area.insert(tk.END, f"Summary:\n{summary}\n")
                output_area.insert(tk.END, "=" * 80 + "\n\n")
                output_area.see(tk.END)
            status_label.config(text="Crawl complete.")
        except Exception as e:
            status_label.config(text="Error during crawl.")
            messagebox.showerror("Crawl Error", f"An error occurred: {e}")
    threading.Thread(target=crawl_thread).start()

def create_gui():
    import subprocess
    root = tk.Tk()
    root.title("Arxiv Paper Pulse GUI")

    # Update the persistent warning label based on recent_days value.
    def update_warning(*args):
        try:
            days = int(recent_days_var.get())
        except ValueError:
            days = 0
        if days > 7:
            warning_label.config(
                text="Warning: Using a date filter greater than 7 days may freeze or crash your computer."
            )
        else:
            warning_label.config(text="")

    recent_days_var = tk.StringVar(value="7")
    recent_days_var.trace_add("write", update_warning)

    installed_models = get_installed_ollama_models()
    if not installed_models:
        installed_models = ["No models found"]

    input_frame = tk.Frame(root)
    input_frame.pack(padx=10, pady=10, fill=tk.X)

    tk.Label(input_frame, text="Search Query:").grid(row=0, column=0, sticky=tk.W)
    query_entry = tk.Entry(input_frame, width=50)
    query_entry.grid(row=0, column=1, padx=5)
    query_entry.insert(0, "AI")

    tk.Label(input_frame, text="Max Results:").grid(row=1, column=0, sticky=tk.W)
    max_results_entry = tk.Entry(input_frame, width=10)
    max_results_entry.grid(row=1, column=1, sticky=tk.W, padx=5)
    max_results_entry.insert(0, "10")

    tk.Label(input_frame, text="Recent Days (set to 7 for last week):").grid(row=2, column=0, sticky=tk.W)
    recent_days_entry = tk.Entry(input_frame, width=10, textvariable=recent_days_var)
    recent_days_entry.grid(row=2, column=1, sticky=tk.W, padx=5)

    warning_label = tk.Label(input_frame, text="", fg="red")
    warning_label.grid(row=3, column=0, columnspan=2, sticky=tk.W)

    tk.Label(input_frame, text="Model:").grid(row=4, column=0, sticky=tk.W)
    model_var = tk.StringVar()
    model_var.set(installed_models[0])
    model_menu = tk.OptionMenu(input_frame, model_var, *installed_models)
    model_menu.grid(row=4, column=1, sticky=tk.W, padx=5)

    button_frame = tk.Frame(root)
    button_frame.pack(padx=10, pady=5, fill=tk.X)

    def local_check_total():
        try:
            days = int(recent_days_var.get())
        except ValueError:
            days = 7
        check_total(query_entry.get(), days)
    check_total_button = tk.Button(button_frame, text="Check Total", command=local_check_total)
    check_total_button.pack(side=tk.LEFT, padx=5)

    def run_crawl_gui():
        try:
            days = int(recent_days_var.get())
        except ValueError:
            days = 7
        def crawl_thread():
            status_label.config(text="Crawling...")
            try:
                summarizer = ArxivSummarizer(
                    max_results=int(max_results_entry.get() or "10"),
                    query=query_entry.get(),
                    model=model_var.get()
                )
                raw_data = summarizer.fetch_raw_data(force_pull=True)

                if days > 0:
                    filtered_data = []
                    now = datetime.datetime.utcnow()
                    for paper in raw_data:
                        updated_str = paper.get("updated")
                        if updated_str:
                            paper_date = parse_date(updated_str)
                            if (now - paper_date).days <= days:
                                filtered_data.append(paper)
                    raw_data = filtered_data

                new_articles = []
                for paper in raw_data:
                    unique_id = get_unique_id(paper)
                    if unique_id and unique_id not in pulled_article_ids:
                        new_articles.append(paper)
                        pulled_article_ids.add(unique_id)

                output_area.delete("1.0", tk.END)
                total = len(new_articles)
                for i, paper in enumerate(new_articles, start=1):
                    msg = f"Summarizing paper {i}/{total}: {paper['title']}\n"
                    output_area.insert(tk.END, msg)
                    output_area.see(tk.END)
                    summary = summarizer.ollama_summarize(paper["abstract"])
                    paper["summary"] = summary
                    output_area.insert(tk.END, f"Summary:\n{summary}\n")
                    output_area.insert(tk.END, "=" * 80 + "\n\n")
                    output_area.see(tk.END)
                status_label.config(text="Crawl complete.")
            except Exception as e:
                status_label.config(text="Error during crawl.")
                messagebox.showerror("Crawl Error", f"An error occurred: {e}")
        threading.Thread(target=crawl_thread).start()

    crawl_button = tk.Button(button_frame, text="Crawl", command=run_crawl_gui)
    crawl_button.pack(side=tk.LEFT, padx=5)

    status_label = tk.Label(root, text="Ready", anchor=tk.W)
    status_label.pack(fill=tk.X, padx=10, pady=(0,10))

    output_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=80, height=20)
    output_area.pack(padx=10, pady=10)

    return root, query_entry, max_results_entry, output_area, status_label, model_var, recent_days_var

def main():
    root, *_ = create_gui()
    root.mainloop()

class ArticleSelectionDialog(tk.Toplevel):
    """Dialog window for selecting articles to summarize"""

    def __init__(self, parent, papers):
        super().__init__(parent)
        self.title("Select Articles to Summarize")
        self.papers = papers
        self.selected_indices = []
        self.create_widgets()
        self.result = None

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Position near parent
        self.geometry(f"+{parent.winfo_rootx() + 50}+{parent.winfo_rooty() + 50}")

    def create_widgets(self):
        frame = tk.Frame(self, padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # Label
        tk.Label(frame, text="Select articles to summarize:", font=("Helvetica", 12)).pack(anchor=tk.W, pady=(0, 10))

        # Create scrolled frame for checkboxes
        canvas = tk.Canvas(frame, borderwidth=0)
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack scroll components
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Checkboxes for articles
        self.vars = []
        for i, paper in enumerate(self.papers):
            var = tk.IntVar(value=1)  # Default selected
            self.vars.append(var)
            cb = tk.Checkbutton(scrollable_frame, text=paper['title'], variable=var,
                               anchor=tk.W, justify=tk.LEFT, wraplength=500)
            cb.pack(fill=tk.X, padx=5, pady=2, anchor=tk.W)

        # Buttons frame
        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)

        # Selection helpers
        select_all_btn = tk.Button(btn_frame, text="Select All", command=self.select_all)
        select_all_btn.pack(side=tk.LEFT, padx=5)

        select_none_btn = tk.Button(btn_frame, text="Select None", command=self.select_none)
        select_none_btn.pack(side=tk.LEFT, padx=5)

        # Control buttons
        cancel_btn = tk.Button(btn_frame, text="Cancel", command=self.cancel)
        cancel_btn.pack(side=tk.RIGHT, padx=5)

        ok_btn = tk.Button(btn_frame, text="Summarize Selected", command=self.ok)
        ok_btn.pack(side=tk.RIGHT, padx=5)

    def select_all(self):
        for var in self.vars:
            var.set(1)

    def select_none(self):
        for var in self.vars:
            var.set(0)

    def ok(self):
        self.selected_indices = [i for i, var in enumerate(self.vars) if var.get() == 1]
        self.result = [self.papers[i] for i in self.selected_indices]
        self.destroy()

    def cancel(self):
        self.result = None
        self.destroy()

class ArxivPulseGUI:
    """
    GUI for the ArXiv Paper Pulse application.
    Allows users to input a query, select how many papers to fetch,
    and see a list of articles before choosing which ones to summarize.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("ArXiv Paper Pulse")
        self.root.geometry("800x600")
        self.create_widgets()
        self.summarizer = None
        self.progress_var = tk.DoubleVar()

    def create_widgets(self):
        # Main frame
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = tk.Label(main_frame, text="ArXiv Paper Pulse", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=(0, 20))

        # Query frame
        query_frame = tk.Frame(main_frame)
        query_frame.pack(fill=tk.X, pady=10)

        tk.Label(query_frame, text="Search Query:").pack(side=tk.LEFT)
        self.query_entry = tk.Entry(query_frame, width=40)
        self.query_entry.insert(0, "cat:cs.AI")
        self.query_entry.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)

        # Get total button
        check_btn = tk.Button(query_frame, text="Check Total", command=self.check_total_articles)
        check_btn.pack(side=tk.RIGHT)

        # Max results frame
        max_frame = tk.Frame(main_frame)
        max_frame.pack(fill=tk.X, pady=10)

        tk.Label(max_frame, text="Number of Articles:").pack(side=tk.LEFT)
        self.max_var = tk.StringVar(value="10")
        self.max_entry = tk.Entry(max_frame, textvariable=self.max_var, width=5)
        self.max_entry.pack(side=tk.LEFT, padx=10)

        # Date filter frame
        date_frame = tk.Frame(main_frame)
        date_frame.pack(fill=tk.X, pady=10)

        tk.Label(date_frame, text="Recent Days Filter:").pack(side=tk.LEFT)
        self.days_var = tk.StringVar(value="7")
        self.days_entry = tk.Entry(date_frame, textvariable=self.days_var, width=5)
        self.days_entry.pack(side=tk.LEFT, padx=10)

        # Ollama model selection
        model_frame = tk.Frame(main_frame)
        model_frame.pack(fill=tk.X, pady=10)

        tk.Label(model_frame, text="Ollama Model:").pack(side=tk.LEFT)

        # Get list of installed models
        models = get_installed_ollama_models()
        default_model = models[0] if models else "llama2"

        self.model_var = tk.StringVar(value=default_model)
        model_dropdown = tk.OptionMenu(model_frame, self.model_var, *models)
        model_dropdown.pack(side=tk.LEFT, padx=10)

        # Fetch button
        self.fetch_btn = tk.Button(main_frame, text="Fetch Articles", command=self.fetch_articles)
        self.fetch_btn.pack(pady=20)

        # Progress bar
        self.progress_frame = tk.Frame(main_frame)
        self.progress_frame.pack(fill=tk.X, pady=10)

        self.progress_bar = tk.ttk.Progressbar(
            self.progress_frame, orient=tk.HORIZONTAL,
            length=100, mode='determinate', variable=self.progress_var
        )
        self.progress_bar.pack(fill=tk.X)

        self.status_label = tk.Label(self.progress_frame, text="Ready")
        self.status_label.pack(pady=5)

        # Output frame
        output_frame = tk.Frame(main_frame)
        output_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Output text
        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, height=15)
        self.output_text.pack(fill=tk.BOTH, expand=True)

        # Bottom frame with open button
        bottom_frame = tk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=10)

        self.open_btn = tk.Button(bottom_frame, text="Open Latest Briefing", command=self.open_briefing)
        self.open_btn.pack(side=tk.RIGHT)
        self.open_btn.config(state=tk.DISABLED)  # Disabled until briefing exists

    def check_total_articles(self):
        """Check how many articles are available for the query in the specified time range"""
        query = self.query_entry.get().strip()
        if not query:
            messagebox.showerror("Error", "Please enter a search query")
            return

        try:
            days = int(self.days_var.get())
            if days <= 0:
                messagebox.showerror("Error", "Days must be a positive number")
                return
        except ValueError:
            messagebox.showerror("Error", "Days must be a number")
            return

        self.status_label.config(text=f"Checking total articles for '{query}'...")
        # Run in a separate thread to keep UI responsive
        threading.Thread(target=check_total, args=(query, days), daemon=True).start()

    def fetch_articles(self):
        """Fetch articles based on the query and max results"""
        query = self.query_entry.get().strip()
        if not query:
            messagebox.showerror("Error", "Please enter a search query")
            return

        try:
            max_results = int(self.max_var.get())
            if max_results <= 0:
                messagebox.showerror("Error", "Number of articles must be positive")
                return
        except ValueError:
            messagebox.showerror("Error", "Number of articles must be a number")
            return

        model = self.model_var.get()

        # Disable UI during fetching
        self.fetch_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Fetching articles...")
        self.output_text.delete(1.0, tk.END)
        self.progress_var.set(0)

        # Create summarizer
        self.summarizer = ArxivSummarizer(max_results=max_results, model=model, query=query)

        # Run in a separate thread
        threading.Thread(target=self._do_fetch_articles, daemon=True).start()

    def _do_fetch_articles(self):
        """Background thread for fetching articles"""
        try:
            # Fetch the raw data
            raw_data = self.summarizer.fetch_raw_data(force_pull=True)

            # Update UI in the main thread
            self.root.after(0, lambda: self._show_fetched_articles(raw_data))
        except Exception as e:
            # Show error in main thread
            self.root.after(0, lambda: messagebox.showerror("Error", f"Error fetching articles: {str(e)}"))
            self.root.after(0, lambda: self.fetch_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.status_label.config(text="Error fetching articles"))

    def _show_fetched_articles(self, papers):
        """Display the fetched articles and prompt for selection"""
        self.status_label.config(text=f"Fetched {len(papers)} articles")

        # Display in output text
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, f"Found {len(papers)} articles for '{self.summarizer.query}'\n\n")

        for i, paper in enumerate(papers, 1):
            self.output_text.insert(tk.END, f"{i}. {paper['title']}\n")
            self.output_text.insert(tk.END, f"   Published: {paper['published']}\n\n")

        # Open selection dialog
        selection_dialog = ArticleSelectionDialog(self.root, papers)
        self.root.wait_window(selection_dialog)

        # Process selection result
        if selection_dialog.result is not None and selection_dialog.result:
            selected_papers = selection_dialog.result
            self.status_label.config(text=f"Selected {len(selected_papers)} articles for summarization")

            # Ask for confirmation
            proceed = messagebox.askyesno("Confirmation",
                f"Summarize {len(selected_papers)} selected articles?\n"
                "This may take some time depending on your local model's speed.")

            if proceed:
                self.summarize_selected_papers(selected_papers)
            else:
                self.fetch_btn.config(state=tk.NORMAL)
        else:
            self.status_label.config(text="No articles selected")
            self.fetch_btn.config(state=tk.NORMAL)

    def summarize_selected_papers(self, selected_papers):
        """Summarize the selected papers"""
        self.status_label.config(text="Starting summarization...")
        self.progress_var.set(0)
        self.output_text.delete(1.0, tk.END)

        # Start the summarization in a background thread
        threading.Thread(target=self._do_summarize_papers,
                        args=(selected_papers,), daemon=True).start()

    def _do_summarize_papers(self, selected_papers):
        """Background thread for summarizing papers"""
        try:
            total_papers = len(selected_papers)

            # Initialize outputs
            summaries = []

            # Initialize a new briefing file
            self.summarizer.initialize_briefing_file()
            briefing_path = self.summarizer.briefing_file

            # Process each paper
            for i, paper in enumerate(selected_papers, 1):
                # Update progress
                progress_pct = (i-1) / total_papers * 100
                self.root.after(0, lambda: self.progress_var.set(progress_pct))
                self.root.after(0, lambda: self.status_label.config(
                    text=f"Summarizing paper {i}/{total_papers}: {paper['title'][:40]}..."
                ))

                # Generate summary if not already present
                if "summary" not in paper:
                    paper["summary"] = self.summarizer.ollama_summarize(paper["abstract"])

                # Add to summaries list and update briefing
                summaries.append(paper)
                self.summarizer.update_briefing_report(paper)

                # Show progress in output text
                self.root.after(0, lambda: self._update_output_text(
                    f"✓ Summarized ({i}/{total_papers}): {paper['title']}\n"
                ))

            # Generate final briefing
            self.root.after(0, lambda: self.status_label.config(text="Generating final synthesis..."))
            self.summarizer.generate_final_briefing()

            # Update UI when complete
            self.root.after(0, lambda: self._summarization_complete(briefing_path))

        except Exception as e:
            # Show error in main thread
            self.root.after(0, lambda: messagebox.showerror("Error", f"Error during summarization: {str(e)}"))
            self.root.after(0, lambda: self.fetch_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.status_label.config(text="Error during summarization"))

    def _update_output_text(self, text):
        """Update the output text widget with new content"""
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)  # Scroll to the end

    def _summarization_complete(self, briefing_path):
        """Called when summarization is complete"""
        self.progress_var.set(100)
        self.status_label.config(text="Summarization complete!")
        self.fetch_btn.config(state=tk.NORMAL)
        self.open_btn.config(state=tk.NORMAL)

        # Show success message with path to briefing
        self._update_output_text("\n" + "="*40 + "\n")
        self._update_output_text(f"Briefing document saved to:\n{briefing_path}\n")
        self._update_output_text("="*40 + "\n")

        # Offer to open the briefing
        open_now = messagebox.askyesno("Summarization Complete",
            f"Briefing document has been saved to:\n{briefing_path}\n\nDo you want to open it now?")

        if open_now:
            self.open_briefing(briefing_path)

    def open_briefing(self, path=None):
        """Open the latest briefing document"""
        try:
            if path is None:
                # Find the latest briefing
                briefing_dir = Path(config.BRIEFING_DIR)
                files = list(briefing_dir.glob("*_briefing.md"))
                if not files:
                    messagebox.showerror("Error", "No briefing files found")
                    return

                path = sorted(files)[-1]  # Get the latest file

            # Open the file with the default application
            import os
            import platform
            import subprocess

            if platform.system() == 'Darwin':  # macOS
                subprocess.call(('open', path))
            elif platform.system() == 'Windows':  # Windows
                os.startfile(path)
            else:  # Linux variants
                subprocess.call(('xdg-open', path))

        except Exception as e:
            messagebox.showerror("Error", f"Error opening briefing: {str(e)}")

def main():
    root = tk.Tk()
    app = ArxivPulseGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
