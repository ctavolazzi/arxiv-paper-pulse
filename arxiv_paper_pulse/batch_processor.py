# arxiv_paper_pulse/batch_processor.py

import time
from typing import List, Dict, Optional
from google import genai
from google.genai import types
from . import config


class BatchPaperProcessor:
    """
    Process papers asynchronously using Gemini Batch API.
    Batch processing offers ~50% cost savings vs real-time processing.
    """

    def __init__(self, model=None, api_key=None):
        """
        Initialize batch processor.

        Args:
            model: Model to use (default from config)
            api_key: API key (default from config)
        """
        self.model = model or config.DEFAULT_MODEL
        self.client = genai.Client(api_key=api_key or config.GEMINI_API_KEY)

    def _create_batch_request(self, paper, system_instruction=None):
        """
        Create a batch request for a single paper.

        Args:
            paper: Paper dict with abstract or prompt
            system_instruction: Optional system instruction

        Returns:
            Batch request dict
        """
        if system_instruction is None:
            system_instruction = """You are an expert scientific research analyst.
Provide comprehensive, insightful analyses of research papers."""

        prompt = config.SUMMARY_PROMPT.format(
            paper.get("abstract", paper.get("text", ""))
        )

        config_obj = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.7,
            top_p=0.95,
            top_k=40
        )

        return {
            "model": f"models/{self.model}",
            "contents": [{"parts": [{"text": prompt}]}],
            "config": config_obj
        }

    def submit_batch(self, papers: List[Dict], system_instruction=None) -> str:
        """
        Submit papers for batch processing.

        Args:
            papers: List of paper dicts
            system_instruction: Optional system instruction

        Returns:
            Batch job ID
        """
        if len(papers) == 0:
            raise ValueError("No papers provided for batch processing")

        print(f"Submitting {len(papers)} papers for batch processing...")

        # Create batch requests
        batch_requests = []
        for paper in papers:
            try:
                request = self._create_batch_request(paper, system_instruction)
                batch_requests.append(request)
            except Exception as e:
                print(f"Failed to create request for {paper.get('title', 'Unknown')}: {e}")

        if not batch_requests:
            raise ValueError("No valid batch requests could be created")

        try:
            # Submit batch job (Note: Batch API structure may vary)
            # This is a placeholder - actual implementation depends on SDK version
            batch_job = self.client.batches.create(requests=batch_requests)
            print(f"Batch job submitted: {batch_job.id}")
            return batch_job.id
        except AttributeError:
            # Batch API might not be available in all SDK versions
            print("Warning: Batch API not available in this SDK version")
            print("Falling back to sequential processing...")
            return None

    def check_batch_status(self, batch_id: str) -> Dict:
        """
        Check status of a batch job.

        Args:
            batch_id: Batch job ID

        Returns:
            Status dict with state, progress, etc.
        """
        try:
            batch_job = self.client.batches.get(batch_id)
            return {
                "id": batch_id,
                "state": getattr(batch_job, 'state', 'UNKNOWN'),
                "created_at": getattr(batch_job, 'created_at', None),
                "completed_at": getattr(batch_job, 'completed_at', None),
            }
        except Exception as e:
            return {"id": batch_id, "error": str(e)}

    def wait_for_completion(self, batch_id: str, max_wait_time=3600, check_interval=30) -> Dict:
        """
        Wait for batch job to complete.

        Args:
            batch_id: Batch job ID
            max_wait_time: Maximum time to wait in seconds (default 1 hour)
            check_interval: How often to check status in seconds

        Returns:
            Final status dict
        """
        start_time = time.time()
        print(f"Waiting for batch job {batch_id} to complete...")

        while time.time() - start_time < max_wait_time:
            status = self.check_batch_status(batch_id)
            state = status.get("state", "UNKNOWN")

            if state in ["SUCCEEDED", "COMPLETED"]:
                print(f"Batch job {batch_id} completed successfully")
                return status
            elif state in ["FAILED", "CANCELLED"]:
                print(f"Batch job {batch_id} {state.lower()}")
                return status

            elapsed = int(time.time() - start_time)
            print(f"Batch job still processing... ({elapsed}s elapsed)")
            time.sleep(check_interval)

        print(f"Timeout waiting for batch job {batch_id}")
        return self.check_batch_status(batch_id)

    def get_batch_results(self, batch_id: str) -> List[Dict]:
        """
        Get results from a completed batch job.

        Args:
            batch_id: Batch job ID

        Returns:
            List of result dicts
        """
        try:
            batch_job = self.client.batches.get(batch_id)
            results = []

            # Extract results from batch job
            # Structure depends on SDK implementation
            if hasattr(batch_job, 'responses'):
                for response in batch_job.responses:
                    results.append({
                        "text": getattr(response, 'text', ''),
                        "usage": getattr(response, 'usage_metadata', {})
                    })

            return results
        except Exception as e:
            print(f"Error getting batch results: {e}")
            return []

