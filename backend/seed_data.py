import os
import sys

# Ensure backend directory is on Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base, SessionLocal
from app.models.user import User
from app.models.repository import Repository
from app.models.pull_request import PullRequest
from app.models.review import ReviewComment
from app.models.security import SecurityFinding
from app.models.architecture import ArchitectureFinding
from app.models.report import Report
from app.api.auth import hash_password

def seed():
    print("[SEEDING] Seeding CodeGuard AI Database...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Clear existing data
    db.query(Report).delete()
    db.query(ArchitectureFinding).delete()
    db.query(SecurityFinding).delete()
    db.query(ReviewComment).delete()
    db.query(PullRequest).delete()
    db.query(Repository).delete()
    db.query(User).delete()
    db.commit()

    # 1. Demo User
    user = User(
        username="admin",
        email="admin@codeguard.ai",
        hashed_password=hash_password("admin123"),
        avatar_url="https://api.dicebear.com/7.x/bottts/svg?seed=admin"
    )
    db.add(user)
    db.commit()

    # 2. Demo Repositories
    repo1 = Repository(
        name="payment-service",
        full_name="codeguard/payment-service",
        owner="codeguard",
        default_branch="main",
        is_private=True,
        description="Core Stripe & PayPal Payment Gateway integration microservice.",
        language="Python",
        quality_score=78,
        security_score=65,
        webhook_active=True
    )
    repo2 = Repository(
        name="web-dashboard",
        full_name="codeguard/web-dashboard",
        owner="codeguard",
        default_branch="main",
        is_private=False,
        description="React & TypeScript Frontend Dashboard for analytics.",
        language="TypeScript",
        quality_score=92,
        security_score=95,
        webhook_active=True
    )
    repo3 = Repository(
        name="auth-service",
        full_name="codeguard/auth-service",
        owner="codeguard",
        default_branch="main",
        is_private=True,
        description="OAuth2 & JWT Identity Provider.",
        language="Go",
        quality_score=84,
        security_score=88,
        webhook_active=True
    )
    db.add_all([repo1, repo2, repo3])
    db.commit()

    # Sample Diffs
    diff_payment = """
diff --git a/services/payment_processor.py b/services/payment_processor.py
--- a/services/payment_processor.py
+++ b/services/payment_processor.py
@@ -14,8 +14,15 @@ class PaymentProcessor:
+    def process_charge(self, user_id, amount, card_number, cvv):
+        # Hardcoded Stripe Secret Key
+        stripe.api_key = "sk_test_placeholder_mock_key_00000"
+        
+        # Dynamic SQL Injection
+        query = "SELECT * FROM billing_info WHERE user_id = '%s'" % user_id
+        db.execute(query)
+        
+        # N+1 Query in loop
+        for item in cart_items:
+            details = db.query(ItemDetail).filter(ItemDetail.id == item.id).first()
"""

    diff_dashboard = """
diff --git a/src/components/UserProfile.tsx b/src/components/UserProfile.tsx
--- a/src/components/UserProfile.tsx
+++ b/src/components/UserProfile.tsx
@@ -20,6 +20,12 @@ export const UserProfile = ({ userBio }: { userBio: string }) => {
+  return (
+    <div className="profile-container">
+      {/* XSS Vulnerability */}
+      <div dangerouslySetInnerHTML={{ __html: userBio }} />
+    </div>
+  );
 };
"""

    # 3. Pull Requests
    pr1 = PullRequest(
        repository_id=repo1.id,
        number=102,
        title="feat: Add automated recurring subscription billing",
        body="Implements weekly & monthly automatic billing charges with Stripe API integration.",
        author="alex_dev",
        author_avatar="https://api.dicebear.com/7.x/avataaars/svg?seed=alex",
        head_branch="feature/subscription-billing",
        base_branch="main",
        state="open",
        status="completed",
        quality_score=68,
        security_score=45,
        architecture_score=72,
        overall_score=62,
        summary="Critical security vulnerabilities detected: Hardcoded Stripe Secret Key & Raw SQL concatenation. Refactor required before merging.",
        diff_data={"raw": diff_payment, "files": [
            {
                "filename": "services/payment_processor.py",
                "additions": 15,
                "deletions": 2,
                "added_lines": [
                    {"line_number": 16, "content": "stripe.api_key = \"sk_test_placeholder_mock_key_00000\""},
                    {"line_number": 19, "content": "query = \"SELECT * FROM billing_info WHERE user_id = '%s'\" % user_id"},
                    {"line_number": 23, "content": "details = db.query(ItemDetail).filter(ItemDetail.id == item.id).first()"}
                ]
            }
        ]}
    )

    pr2 = PullRequest(
        repository_id=repo2.id,
        number=45,
        title="refactor: Render user bio HTML in profile card",
        body="Allows rich text preview for member biographies.",
        author="sarah_frontend",
        author_avatar="https://api.dicebear.com/7.x/avataaars/svg?seed=sarah",
        head_branch="refactor/user-bio",
        base_branch="main",
        state="open",
        status="completed",
        quality_score=90,
        security_score=70,
        architecture_score=88,
        overall_score=83,
        summary="Cross-Site Scripting (XSS) risk found in UserProfile component. Recommend DOMPurify sanitization.",
        diff_data={"raw": diff_dashboard, "files": [
            {
                "filename": "src/components/UserProfile.tsx",
                "additions": 6,
                "deletions": 1,
                "added_lines": [
                    {"line_number": 24, "content": "<div dangerouslySetInnerHTML={{ __html: userBio }} />"}
                ]
            }
        ]}
    )
    db.add_all([pr1, pr2])
    db.commit()

    # 4. Review Comments
    rc1 = ReviewComment(
        pull_request_id=pr1.id,
        file_path="services/payment_processor.py",
        line_number=16,
        severity="Critical",
        category="Security",
        title="Exposed Hardcoded API Key",
        description="Stripe secret key `sk_live_...` is hardcoded directly in Python source code.",
        why_it_matters="Hardcoded keys committed to git repositories can be leaked, allowing attackers to make unauthorized charges.",
        suggested_fix="Move the Stripe secret key to an environment variable (`os.getenv('STRIPE_SECRET_KEY')`) or AWS Secrets Manager.",
        example_code="import os\nstripe.api_key = os.getenv('STRIPE_SECRET_KEY')",
        status="open"
    )

    rc2 = ReviewComment(
        pull_request_id=pr1.id,
        file_path="services/payment_processor.py",
        line_number=19,
        severity="Critical",
        category="Security",
        title="SQL Injection Vulnerability",
        description="Dynamic string formatting `%s` used inside raw SQL query execution.",
        why_it_matters="Allows attackers to perform SQL Injection attacks and bypass authentication or exfiltrate database records.",
        suggested_fix="Use ORM parameterized query syntax or bound parameters.",
        example_code="query = db.query(BillingInfo).filter(BillingInfo.user_id == user_id)",
        status="open"
    )

    rc3 = ReviewComment(
        pull_request_id=pr1.id,
        file_path="services/payment_processor.py",
        line_number=23,
        severity="High",
        category="Performance",
        title="N+1 Query in Loop",
        description="Executing individual database queries inside a cart iteration loop.",
        why_it_matters="Causes N+1 database network roundtrips, degrading response times under high concurrency.",
        suggested_fix="Batch fetch item details before the loop using `filter(ItemDetail.id.in_(item_ids))`.",
        example_code="item_ids = [item.id for item in cart_items]\ndetails_map = {d.id: d for d in db.query(ItemDetail).filter(ItemDetail.id.in_(item_ids)).all()}",
        status="open"
    )

    rc4 = ReviewComment(
        pull_request_id=pr2.id,
        file_path="src/components/UserProfile.tsx",
        line_number=24,
        severity="High",
        category="Security",
        title="Unsanitized HTML Rendering (XSS)",
        description="Using `dangerouslySetInnerHTML` with untrusted `userBio` property.",
        why_it_matters="Allows arbitrary JavaScript execution in victim users' browsers (Stored XSS).",
        suggested_fix="Sanitize content with DOMPurify before setting innerHTML.",
        example_code="import DOMPurify from 'dompurify';\n<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(userBio) }} />",
        status="open"
    )
    db.add_all([rc1, rc2, rc3, rc4])

    # 5. Security Findings
    sf1 = SecurityFinding(
        repository_id=repo1.id,
        pull_request_id=pr1.id,
        vulnerability_type="Exposed Secret (Stripe)",
        cve_id="CWE-798",
        severity="Critical",
        file_path="services/payment_processor.py",
        line_number=16,
        raw_snippet="stripe.api_key = \"sk_test_placeholder_mock_key_00000\"",
        description="Hardcoded Stripe Secret Key detected in repository.",
        recommendation="Revoke Stripe API Key immediately and use env var.",
        risk_score=95,
        status="open"
    )
    sf2 = SecurityFinding(
        repository_id=repo1.id,
        pull_request_id=pr1.id,
        vulnerability_type="SQL Injection",
        cve_id="CVE-2023-SQLI",
        severity="Critical",
        file_path="services/payment_processor.py",
        line_number=19,
        raw_snippet="query = \"SELECT * FROM billing_info WHERE user_id = '%s'\" % user_id",
        description="Unparameterized SQL string formatting.",
        recommendation="Use parameterized SQLAlchemy queries.",
        risk_score=90,
        status="open"
    )
    db.add_all([sf1, sf2])

    # 6. Architecture Findings
    af1 = ArchitectureFinding(
        repository_id=repo1.id,
        pull_request_id=pr1.id,
        principle_violated="Single Responsibility Principle (SRP)",
        severity="High",
        component="PaymentProcessor",
        description="PaymentProcessor handles database access, billing calculation, and HTTP notifications in one monolithic class.",
        recommendation="Decompose into PaymentService, BillingRepository, and NotificationGateway.",
        design_pattern_suggested="Repository & Gateway Pattern",
        status="open"
    )
    db.add(af1)

    db.commit()
    print("[SUCCESS] Database seeding complete!")

if __name__ == "__main__":
    seed()
