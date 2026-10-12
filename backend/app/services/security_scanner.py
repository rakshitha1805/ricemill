import re
from typing import List, Dict, Any

class SecurityScanner:
    """Automated security analysis engine for secret detection, OWASP vulnerabilities, and risk scoring."""

    SECRET_PATTERNS = [
        (r'AKIA[0-9A-Z]{16}', "AWS Access Key ID", "Critical", 95),
        (r'sk_live_[0-9a-zA-Z]{24}', "Stripe Secret Key", "Critical", 95),
        (r'sk-[a-zA-Z0-9]{32,48}', "OpenAI API Key", "High", 85),
        (r'ghp_[a-zA-Z0-9]{36}', "GitHub Personal Access Token", "Critical", 90),
        (r'-----BEGIN PRIVATE KEY-----', "RSA/ECC Private Key", "Critical", 99),
        (r'(?i)(password|secret|passwd|auth_token)\s*=\s*["\'][A-Za-z0-9@#$%^&*!~_]{6,}["\']', "Hardcoded Password/Secret", "High", 80),
        (r'postgres://[^:]+:[^@]+@', "PostgreSQL Connection String with Credentials", "High", 85),
        (r'mongodb\+srv://[^:]+:[^@]+@', "MongoDB Connection String with Credentials", "High", 85)
    ]

    OWASP_RULES = [
        # SQL Injection
        (r'(?i)(select|insert|update|delete)\s+.*\s+from\s+.*(%s|\$\{.*\}|\+\s*req\.)', "SQL Injection", "CVE-2023-SQLI", "Critical", 90,
         "Raw dynamic SQL concatenation detected. Input parameters are directly concatenated into the database query string.",
         "Use parameterized queries or ORM query builders (e.g. SQLAlchemy, Prisma, Prepared Statements) to isolate user input from SQL commands."),
        
        (r'(?i)cursor\.execute\(["\'].*%[s|d].*["\']\s*%', "SQL Injection in Python Cursor", "CVE-2023-SQLI-PY", "Critical", 90,
         "Python string formatting inside cursor.execute() bypasses SQL parameterization.",
         "Pass parameters as a tuple in the second argument: cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))"),

        # Cross-Site Scripting (XSS)
        (r'dangerouslySetInnerHTML\s*=\s*\{\s*\{\s*__html\s*:\s*', "Cross-Site Scripting (XSS)", "OWASP-A03-XSS", "High", 75,
         "Unsanitized HTML rendering via dangerouslySetInnerHTML exposes users to Stored/Reflected XSS attacks.",
         "Sanitize dynamic HTML content with DOMPurify before rendering, or use native React JSX escaping."),

        (r'eval\(|setTimeout\(["\'].*["\']|setInterval\(["\'].*["\']', "Dynamic Code Execution (eval)", "OWASP-A03-EVAL", "Critical", 92,
         "Use of eval() or dynamic code string execution enables arbitrary code execution vulnerabilities.",
         "Avoid eval(). Use JSON.parse() or structured logic handlers instead."),

        # Command Injection
        (r'os\.system\(|subprocess\.Popen\(.*shell\s*=\s*True|child_process\.exec\(', "Command Injection", "OWASP-A03-CMDI", "Critical", 95,
         "Executing system commands with shell=True or unescaped parameters allows attackers to execute arbitrary shell commands.",
         "Pass command arguments as a list with shell=False: subprocess.run(['ls', '-l', path], check=True)"),

        # Path Traversal
        (r'open\(.*req\.(params|query|body).*|fs\.readFile\(.*req\.', "Path Traversal", "OWASP-A01-PATH", "High", 80,
         "User-supplied input passed directly into file opening functions allows arbitrary file read via ../ manipulation.",
         "Validate file paths using os.path.abspath() and verify they remain within an allowed sandbox directory."),

        # Insecure Authentication / Cryptography
        (r'md5\(|sha1\(', "Weak Cryptographic Hash (MD5/SHA1)", "OWASP-A02-CRYPTO", "Medium", 60,
         "MD5 and SHA-1 algorithms are cryptographically broken and vulnerable to collision attacks.",
         "Upgrade to SHA-256 or bcrypt/argon2id for password hashing.")
    ]

    KNOWN_VULNERABLE_DEPS = [
        ("log4j", "2.14.1", "Log4Shell RCE Vulnerability", "CVE-2021-44228", "Critical", 100),
        ("requests", "2.20.0", "Insecure SSL Certificate Verification", "CVE-2018-18074", "Medium", 60),
        ("express", "4.15.0", "ReDoS in serve-static dependency", "CVE-2017-16119", "High", 75),
        ("pyyaml", "5.1", "Arbitrary Code Execution via Load", "CVE-2020-14343", "High", 85)
    ]

    def scan_diff(self, parsed_files: List[Dict[str, Any]], repo_id: int, pr_id: int = None) -> Dict[str, Any]:
        findings = []
        total_risk = 0

        for file_info in parsed_files:
            filename = file_info.get("filename", "")
            added_lines = file_info.get("added_lines", [])

            for line_obj in added_lines:
                line_num = line_obj.get("line_number")
                content = line_obj.get("content", "")

                # 1. Secret Detection
                for pattern, secret_type, severity, score in self.SECRET_PATTERNS:
                    if re.search(pattern, content):
                        findings.append({
                            "repository_id": repo_id,
                            "pull_request_id": pr_id,
                            "vulnerability_type": f"Exposed Secret: {secret_type}",
                            "cve_id": "CWE-798",
                            "severity": severity,
                            "file_path": filename,
                            "line_number": line_num,
                            "raw_snippet": content.strip(),
                            "description": f"Hardcoded {secret_type} detected in source code.",
                            "recommendation": "Revoke this secret immediately and move credentials to environment variables or a Secret Vault.",
                            "risk_score": score,
                            "status": "open"
                        })
                        total_risk += score

                # 2. OWASP Vulnerability Check
                for pattern, vuln_type, cve, severity, score, desc, rec in self.OWASP_RULES:
                    if re.search(pattern, content):
                        findings.append({
                            "repository_id": repo_id,
                            "pull_request_id": pr_id,
                            "vulnerability_type": vuln_type,
                            "cve_id": cve,
                            "severity": severity,
                            "file_path": filename,
                            "line_number": line_num,
                            "raw_snippet": content.strip(),
                            "description": desc,
                            "recommendation": rec,
                            "risk_score": score,
                            "status": "open"
                        })
                        total_risk += score

            # 3. Dependency File Check (e.g. requirements.txt or package.json)
            if "requirements.txt" in filename or "package.json" in filename:
                for line_obj in added_lines:
                    content = line_obj.get("content", "")
                    for dep, vuln_ver, title, cve, severity, score in self.KNOWN_VULNERABLE_DEPS:
                        if dep in content.lower():
                            findings.append({
                                "repository_id": repo_id,
                                "pull_request_id": pr_id,
                                "vulnerability_type": f"Vulnerable Dependency ({dep})",
                                "cve_id": cve,
                                "severity": severity,
                                "file_path": filename,
                                "line_number": line_obj.get("line_number"),
                                "raw_snippet": content.strip(),
                                "description": f"{title} found in dependency declaration.",
                                "recommendation": f"Upgrade {dep} to the latest secure patch release.",
                                "risk_score": score,
                                "status": "open"
                            })
                            total_risk += score

        # Calculate overall security score (100 is best, 0 is worst)
        if not findings:
            security_score = 98
            overall_risk = 5
        else:
            impact = min(85, sum(f["risk_score"] for f in findings) // max(1, len(findings)))
            security_score = max(10, 100 - impact)
            overall_risk = impact

        return {
            "findings": findings,
            "security_score": security_score,
            "overall_risk": overall_risk,
            "findings_count": len(findings)
        }
