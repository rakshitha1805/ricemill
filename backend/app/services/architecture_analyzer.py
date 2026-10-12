import re
from typing import List, Dict, Any

class ArchitectureAnalyzer:
    """Analyzes architectural health, SOLID principles, design patterns, and coupling."""

    def analyze_diff(self, parsed_files: List[Dict[str, Any]], repo_id: int, pr_id: int = None) -> Dict[str, Any]:
        findings = []

        for file_info in parsed_files:
            filename = file_info.get("filename", "")
            added_lines = file_info.get("added_lines", [])
            full_content = "\n".join([l["content"] for l in added_lines])

            # 1. Single Responsibility Principle (SRP) / God Class
            class_matches = re.findall(r'class\s+([A-Za-z0-9_]+)', full_content)
            def_matches = re.findall(r'def\s+([A-Za-z0-9_]+)', full_content)
            
            if len(class_matches) > 0 and len(def_matches) > 12:
                findings.append({
                    "repository_id": repo_id,
                    "pull_request_id": pr_id,
                    "principle_violated": "Single Responsibility Principle (SRP)",
                    "severity": "High",
                    "component": class_matches[0] if class_matches else filename,
                    "description": f"Class '{class_matches[0]}' defines more than 12 methods in a single file, indicating multiple responsibilities.",
                    "recommendation": "Decompose this class into smaller domain services using composition or sub-modules.",
                    "design_pattern_suggested": "Facade or Strategy Pattern",
                    "status": "open"
                })

            # 2. Dependency Inversion Principle (DIP) / Hardcoded Instantiation
            if re.search(r'self\.[a-zA-Z0-9_]+\s*=\s*(PostgreSQLDatabase|S3Uploader|HttpClient|StripeClient)\(\)', full_content):
                findings.append({
                    "repository_id": repo_id,
                    "pull_request_id": pr_id,
                    "principle_violated": "Dependency Inversion Principle (DIP)",
                    "severity": "High",
                    "component": filename,
                    "description": "Concrete infrastructural dependencies are instantiated directly inside constructor instead of being injected.",
                    "recommendation": "Pass dependencies through constructor parameter injection or use an IoC container interface.",
                    "design_pattern_suggested": "Dependency Injection / Service Locator",
                    "status": "open"
                })

            # 3. Open/Closed Principle (OCP) / Giant switch/if-elif chains
            if len(re.findall(r'if\s+.*:\s*\n\s*elif\s+.*:', full_content)) > 4 or full_content.count("switch (") > 0 and full_content.count("case ") > 5:
                findings.append({
                    "repository_id": repo_id,
                    "pull_request_id": pr_id,
                    "principle_violated": "Open/Closed Principle (OCP)",
                    "severity": "Medium",
                    "component": filename,
                    "description": "Extensive conditional branching (if/elif/switch) detected for type or action handling. Adding new types requires modifying existing logic.",
                    "recommendation": "Encapsulate varied behaviors into strategy objects or polymorphically derived classes.",
                    "design_pattern_suggested": "Strategy Pattern / Factory Pattern",
                    "status": "open"
                })

            # 4. Tight Coupling / Direct Global State access
            if "global " in full_content or "window." in full_content and "localStorage" in full_content:
                findings.append({
                    "repository_id": repo_id,
                    "pull_request_id": pr_id,
                    "principle_violated": "Tight Coupling & Global State Mutation",
                    "severity": "Medium",
                    "component": filename,
                    "description": "Direct mutation of global state couples components tightly to runtime environment side-effects.",
                    "recommendation": "Encapsulate state inside scoped context providers or dedicated state repositories.",
                    "design_pattern_suggested": "Repository / State Provider Pattern",
                    "status": "open"
                })

            # 5. Method parameter overload (>6 parameters)
            param_overloads = re.findall(r'def\s+[A-Za-z0-9_]+\(([^)]*)\)', full_content)
            for params in param_overloads:
                param_count = len([p for p in params.split(',') if p.strip() and p.strip() != 'self' and p.strip() != 'cls'])
                if param_count >= 7:
                    findings.append({
                        "repository_id": repo_id,
                        "pull_request_id": pr_id,
                        "principle_violated": "Long Parameter List Code Smell",
                        "severity": "Low",
                        "component": filename,
                        "description": f"Function accepts {param_count} parameters, making callers fragile and reducing readability.",
                        "recommendation": "Group related arguments into a Parameter Object or Config Data Class.",
                        "design_pattern_suggested": "Builder / Parameter Object Pattern",
                        "status": "open"
                    })

        architecture_score = max(30, 95 - (len(findings) * 12))
        return {
            "findings": findings,
            "architecture_score": architecture_score,
            "findings_count": len(findings)
        }
