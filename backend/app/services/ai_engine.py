import json
import logging
import re
from typing import List, Dict, Any, Optional
from app.config import settings

logger = logging.getLogger("codeguard.ai_engine")

class AICodeAnalysisEngine:
    """Core AI Code Analysis Engine supporting Gemini API with fallback heuristic engine."""

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.AI_MODEL

    async def analyze_pr_diff(self, pr_title: str, pr_body: str, diff_files: List[Dict[str, Any]], security_results: Dict[str, Any], arch_results: Dict[str, Any]) -> Dict[str, Any]:
        """Performs full AI code review analysis combining Security Scanner, Architecture Analyzer, and LLM reasoning."""
        
        # Try Gemini API if API key is provided
        if self.api_key and len(self.api_key.strip()) > 5:
            try:
                gemini_res = await self._analyze_with_gemini(pr_title, pr_body, diff_files)
                if gemini_res:
                    return gemini_res
            except Exception as e:
                logger.warning(f"Gemini API call failed, falling back to heuristic engine: {e}")

        # Fallback to smart heuristic review engine
        return self._heuristic_analysis(pr_title, pr_body, diff_files, security_results, arch_results)

    async def _analyze_with_gemini(self, pr_title: str, pr_body: str, diff_files: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Invokes Google Gemini API for deep code understanding and JSON review comment generation."""
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)

            diff_summary_text = ""
            for f in diff_files[:5]:
                diff_summary_text += f"\n--- File: {f.get('filename')} ---\n"
                for added in f.get('added_lines', [])[:30]:
                    diff_summary_text += f"+ {added.get('content')}\n"

            prompt = f"""
You are CodeGuard AI, a principal software architect and security auditor.
Analyze the following Pull Request diff and generate structured JSON feedback.

PR Title: {pr_title}
PR Description: {pr_body}

Diff snippet:
{diff_summary_text}

Return ONLY valid JSON matching this schema:
{{
  "summary": "Executive summary of the PR and major findings",
  "quality_score": 85,
  "security_score": 90,
  "architecture_score": 80,
  "overall_score": 85,
  "comments": [
    {{
      "file_path": "path/to/file.py",
      "line_number": 15,
      "severity": "High",
      "category": "Security",
      "title": "Short title",
      "description": "Clear explanation of the issue",
      "why_it_matters": "Business/technical risk impact",
      "suggested_fix": "Clear instruction to fix",
      "example_code": "Improved refactored snippet"
    }}
  ]
}}
"""
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2
                )
            )

            if response and response.text:
                data = json.loads(response.text)
                return data
        except Exception as e:
            logger.error(f"Error calling Gemini: {e}")
            return None

    def _heuristic_analysis(self, pr_title: str, pr_body: str, diff_files: List[Dict[str, Any]], security_results: Dict[str, Any], arch_results: Dict[str, Any]) -> Dict[str, Any]:
        """Smart rule-based AI synthesis fallback engine when LLM key is absent or offline."""
        comments = []

        # Convert Security findings into Review Comments
        for sf in security_results.get("findings", []):
            comments.append({
                "file_path": sf["file_path"],
                "line_number": sf.get("line_number", 1),
                "severity": sf["severity"],
                "category": "Security",
                "title": sf["vulnerability_type"],
                "description": sf["description"],
                "why_it_matters": "Security vulnerabilities can allow unauthorized access, data exfiltration, or remote execution in production.",
                "suggested_fix": sf["recommendation"],
                "example_code": f"// Recommended fix for {sf['vulnerability_type']}\n// Always sanitize inputs and avoid hardcoded secrets."
            })

        # Convert Architecture findings into Review Comments
        for af in arch_results.get("findings", []):
            comments.append({
                "file_path": af["component"],
                "line_number": 1,
                "severity": af["severity"],
                "category": "SOLID / Architecture",
                "title": f"Violation: {af['principle_violated']}",
                "description": af["description"],
                "why_it_matters": "Architectural violations lead to high technical debt, fragile unit testing, and rigid module coupling.",
                "suggested_fix": af["recommendation"],
                "example_code": f"// Suggested Design Pattern: {af.get('design_pattern_suggested', 'Dependency Injection')}"
            })

        # General Code Smell & Performance checks across diff files
        for f in diff_files:
            filename = f.get("filename", "")
            added = f.get("added_lines", [])

            for line_obj in added:
                content = line_obj.get("content", "")
                line_num = line_obj.get("line_number", 1)

                # Performance: N+1 query pattern
                if "for " in content and (".query" in content or "objects.filter" in content or "SELECT" in content):
                    comments.append({
                        "file_path": filename,
                        "line_number": line_num,
                        "severity": "High",
                        "category": "Performance",
                        "title": "Potential N+1 Database Query in Loop",
                        "description": "Executing database queries inside an iteration loop causes significant latency and DB connection exhaustion.",
                        "why_it_matters": "N+1 queries degrade API performance exponentially as the dataset grows.",
                        "suggested_fix": "Fetch required entities in batch using eager loading (joinedload / select_related) or IN clauses before entering the loop.",
                        "example_code": "# Before (N+1):\n# for user in users:\n#     posts = db.query(Post).filter(Post.user_id == user.id).all()\n\n# Fixed (Batch Eager Load):\nusers_with_posts = db.query(User).options(joinedload(User.posts)).all()"
                    })

                # Maintainability: Missing error handling in async/Promise
                if ("fetch(" in content or "axios." in content) and "catch" not in content and "try" not in content:
                    comments.append({
                        "file_path": filename,
                        "line_number": line_num,
                        "severity": "Medium",
                        "category": "Maintainability",
                        "title": "Unhandled Async Network Request",
                        "description": "Network API call made without try/catch or .catch() handler.",
                        "why_it_matters": "Uncaught promises can cause silent UI crashes or unhandled server exceptions.",
                        "suggested_fix": "Wrap network requests in a try/catch block and present graceful error state feedback.",
                        "example_code": "try {\n  const res = await fetch('/api/data');\n} catch (err) {\n  console.error('Fetch failed:', err);\n  toast.error('Failed to load data');\n}"
                    })

                # Code Smell: Magic Numbers
                if re.search(r'\b(if|while)\s*\([^)]*\b(86400|3600|1000|60|1024)\b', content):
                    comments.append({
                        "file_path": filename,
                        "line_number": line_num,
                        "severity": "Low",
                        "category": "Code Quality",
                        "title": "Magic Numeric Constant",
                        "description": "Unnamed numeric literal used directly in business logic condition.",
                        "why_it_matters": "Magic numbers obscure business intent and increase maintenance error risk.",
                        "suggested_fix": "Extract numeric values into self-documenting named constants.",
                        "example_code": "SECONDS_IN_DAY = 86,400\n# if elapsed > SECONDS_IN_DAY:"
                    })

        sec_score = security_results.get("security_score", 85)
        arch_score = arch_results.get("architecture_score", 80)
        qual_score = max(40, 100 - (len(comments) * 6))
        overall = (qual_score + sec_score + arch_score) // 3

        summary_text = (
            f"CodeGuard AI completed comprehensive review for PR: '{pr_title}'. "
            f"Identified {len(comments)} review item(s) spanning Security, Architecture, Performance, and Code Quality. "
            f"Overall health score is {overall}/100."
        )

        return {
            "summary": summary_text,
            "quality_score": qual_score,
            "security_score": sec_score,
            "architecture_score": arch_score,
            "overall_score": overall,
            "comments": comments
        }

    async def answer_developer_chat(self, question: str, pr_title: str, review_comments: List[Dict[str, Any]]) -> str:
        """Answers developer questions about a specific PR review using Gemini or intelligent fallback."""
        if self.api_key and len(self.api_key.strip()) > 5:
            try:
                from google import genai
                client = genai.Client(api_key=self.api_key)
                prompt = f"""
You are CodeGuard AI Developer Assistant.
PR Title: {pr_title}
Active Review Comments: {json.dumps(review_comments[:5])}

Developer Question: {question}

Answer concisely, providing code examples where appropriate.
"""
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                logger.warning(f"Gemini chat error: {e}")

        # Fallback chat response generator
        q_lower = question.lower()
        if "security" in q_lower or "vulnerability" in q_lower:
            return f"Regarding security in '{pr_title}': Make sure all secret tokens are stored in environment variables, user inputs are sanitized against SQLi and XSS, and HTTPS endpoints are used."
        elif "fix" in q_lower or "how to" in q_lower:
            return f"To apply the recommended fix for this PR: Review the inline suggestion cards in the Diff Viewer, copy the proposed refactored snippet, replace the lines in your branch, and push a new commit."
        elif "solid" in q_lower or "architecture" in q_lower:
            return f"Architectural analysis for '{pr_title}': Focus on Single Responsibility by splitting multi-purpose classes into dedicated domain services and injecting dependencies via interfaces."
        else:
            return f"CodeGuard Assistant: I have reviewed '{pr_title}'. The primary suggestions focus on improving code maintainability, eliminating potential security risks, and applying recommended design patterns."
