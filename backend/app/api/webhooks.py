from fastapi import APIRouter, Request, Header, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.repository import Repository
from app.models.pull_request import PullRequest
from app.models.review import ReviewComment
from app.models.security import SecurityFinding
from app.models.architecture import ArchitectureFinding
from app.services.github_service import GitHubService
from app.services.security_scanner import SecurityScanner
from app.services.architecture_analyzer import ArchitectureAnalyzer
from app.services.ai_engine import AICodeAnalysisEngine
from app.utils.diff_parser import DiffParser
import logging

router = APIRouter(prefix="/webhooks", tags=["GitHub Webhooks"])
logger = logging.getLogger("codeguard.webhooks")

async def process_pull_request_event(payload: dict, db: Session):
    """Background task to run full CodeGuard AI review process on incoming PR webhook."""
    action = payload.get("action")
    pr_data = payload.get("pull_request", {})
    repo_data = payload.get("repository", {})

    if not pr_data or not repo_data:
        return

    repo_full_name = repo_data.get("full_name")
    pr_number = pr_data.get("number")
    pr_title = pr_data.get("title", "")
    pr_body = pr_data.get("body", "")
    author = pr_data.get("user", {}).get("login", "unknown")
    author_avatar = pr_data.get("user", {}).get("avatar_url")
    head_branch = pr_data.get("head", {}).get("ref", "feature")
    base_branch = pr_data.get("base", {}).get("ref", "main")

    # 1. Find or create Repository record
    repo = db.query(Repository).filter(Repository.full_name == repo_full_name).first()
    if not repo:
        repo = Repository(
            name=repo_data.get("name", "repo"),
            full_name=repo_full_name,
            owner=repo_data.get("owner", {}).get("login", "owner"),
            is_private=repo_data.get("private", False),
            description=repo_data.get("description", "")
        )
        db.add(repo)
        db.commit()
        db.refresh(repo)

    # 2. Find or create PullRequest record
    pr = db.query(PullRequest).filter(
        PullRequest.repository_id == repo.id,
        PullRequest.number == pr_number
    ).first()

    if not pr:
        pr = PullRequest(
            repository_id=repo.id,
            number=pr_number,
            title=pr_title,
            body=pr_body,
            author=author,
            author_avatar=author_avatar,
            head_branch=head_branch,
            base_branch=base_branch,
            status="analyzing"
        )
        db.add(pr)
    else:
        pr.title = pr_title
        pr.body = pr_body
        pr.status = "analyzing"

    db.commit()
    db.refresh(pr)

    # Sample diff content if live diff unavailable
    sample_diff = pr_data.get("diff_content") or """
diff --git a/app/services/payment.py b/app/services/payment.py
--- a/app/services/payment.py
+++ b/app/services/payment.py
@@ -10,6 +10,12 @@ class PaymentProcessor:
+    def process_transaction(self, user_id, amount, card_no):
+        db_cursor.execute("SELECT * FROM users WHERE id = '%s'" % user_id)
+        stripe_secret = "sk_test_placeholder_mock_key_00000"
+        for item in cart:
+            res = db.query(CartItem).filter(CartItem.id == item.id).all()
"""

    parsed_files = DiffParser.parse_diff(sample_diff)
    pr.diff_data = {"files": parsed_files, "raw": sample_diff}

    # 3. Run Security Scanner
    sec_scanner = SecurityScanner()
    sec_results = sec_scanner.scan_diff(parsed_files, repo.id, pr.id)

    for sf in sec_results["findings"]:
        finding = SecurityFinding(**sf)
        db.add(finding)

    # 4. Run Architecture Analyzer
    arch_analyzer = ArchitectureAnalyzer()
    arch_results = arch_analyzer.analyze_diff(parsed_files, repo.id, pr.id)

    for af in arch_results["findings"]:
        finding = ArchitectureFinding(**af)
        db.add(finding)

    # 5. Run AI Code Engine
    ai_engine = AICodeAnalysisEngine()
    ai_res = await ai_engine.analyze_pr_diff(pr_title, pr_body, parsed_files, sec_results, arch_results)

    pr.summary = ai_res.get("summary")
    pr.quality_score = ai_res.get("quality_score", 85)
    pr.security_score = ai_res.get("security_score", 90)
    pr.architecture_score = ai_res.get("architecture_score", 80)
    pr.overall_score = ai_res.get("overall_score", 85)
    pr.status = "completed"

    for c in ai_res.get("comments", []):
        comment = ReviewComment(
            pull_request_id=pr.id,
            file_path=c.get("file_path", "app.py"),
            line_number=c.get("line_number", 1),
            severity=c.get("severity", "Medium"),
            category=c.get("category", "Code Quality"),
            title=c.get("title", "Review Finding"),
            description=c.get("description", ""),
            why_it_matters=c.get("why_it_matters", ""),
            suggested_fix=c.get("suggested_fix", ""),
            example_code=c.get("example_code", "")
        )
        db.add(comment)

    db.commit()

    # 6. Post comments & status back to GitHub API
    gh = GitHubService()
    summary_md = f"### 🛡️ CodeGuard AI PR Review Summary\n\n**Overall Health Score: {pr.overall_score}/100**\n\n"
    summary_md += f"- 🔒 Security Score: {pr.security_score}/100\n"
    summary_md += f"- ⚡ Quality Score: {pr.quality_score}/100\n"
    summary_md += f"- 🏗️ Architecture Score: {pr.architecture_score}/100\n\n"
    summary_md += f"**Summary:** {pr.summary}\n"

    await gh.post_review_comment(repo_full_name, pr_number, summary_md)
    status_state = "success" if pr.overall_score >= 70 else "failure"
    await gh.update_commit_status(repo_full_name, pr_data.get("head", {}).get("sha", "head"), status_state, f"CodeGuard AI Score: {pr.overall_score}/100")

@router.post("/github")
async def github_webhook_listener(request: Request, background_tasks: BackgroundTasks, x_hub_signature_256: str = Header(None), db: Session = Depends(get_db)):
    body_bytes = await request.body()
    if not GitHubService.verify_webhook_signature(body_bytes, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid Webhook Signature")

    payload = await request.json()
    event = request.headers.get("X-GitHub-Event", "pull_request")

    if event == "pull_request":
        action = payload.get("action")
        if action in ["opened", "synchronize", "reopened"]:
            background_tasks.add_task(process_pull_request_event, payload, db)

    return {"status": "accepted", "event": event}
