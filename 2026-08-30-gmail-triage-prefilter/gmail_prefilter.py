#!/usr/bin/env python3
"""
Gmail Foreign Mail Prefilter — Gmail 外文來信 triage 前處理器

功能：在 LLM triage 之前先用 heuristic 規則過濾，明顯偽陽直接排除，
      減少 LLM API 呼叫次數與成本。

用法：
  python3 gmail_prefilter.py [--dry-run] [--min-score N]

範例：
  python3 gmail_prefilter.py              # 正式執行（輸出會處理的信件）
  python3 gmail_prefilter.py --dry-run    # 測試模式，僅顯示過濾邏輯不打 API

輸入來源：gog gmail search（需預先登入）
輸出：JSON 格式的候選信件清單，格式與現有 triage cron prompt 相容
"""

import subprocess
import json
import re
import sys
import argparse
from dataclasses import dataclass, asdict
from typing import Optional

# ─── Heuristic 規則 ───────────────────────────────────────────────────────

# 寄件網域黑名單（明顯行銷/系統信）
DOMAIN_DENYLIST = {
    "10times.com", "eventbrite.com", "mailchimp.com", "sendgrid.net",
    "amazonses.com", "mailgun.org", "postmarkapp.com", "mandrillapp.com",
    "hubspot.com", "marketo.com", "salesforce.com", "zendesk.com",
    "intercom.io", "freshdesk.com", "helpdesk", "no-reply", "noreply",
    "unsub", "unsubscribe", "notify", "notification", "alert", "updates",
    "newsletter", "news", "digest", "notification", "noreply", "no-reply",
    "bounce", "bounced", "daemon", "automated", "system",
    # 常見平台通知（各類 SaaS 平台）
    "slack.com", "zoom.us", "meet.google.com", "notion.so", "asana.com",
    "trello.com", "monday.com", "linear.app", "github.com", "gitlab.com",
    "bitbucket.org", "jira.atlassian.com", "confluence.atlassian.com",
    # 常見訊息/社群平台通知
    "zep.app", "discord.com", "telegram.org", "messenger.facebook.com",
    "LINE", "line.me", "whatsapp.com", "wechat.com",
    # 一般平台通知（盡量完整）
    "getrevue.co", "buttondown.email", "mailjet.com", "sendgrid.com",
    "postgrid.com", "lob.com", "paperform.co", "typeform.com",
    "google.com", "youtube.com", "linkedin.com", "twitter.com", "x.com",
    "facebook.com", "instagram.com", "tiktok.com", "threads.net",
}

# 內文關鍵字黑名單（直接排除）
BODY_KEYWORD_DENYLIST = [
    r"(?i)unsubscribe", r"(?i)manage subscription", r"(?i)view in browser",
    r"(?i)email not displaying", r"(?i)click here to", r"(?i)special offer",
    r"(?i)limited time", r"(?i)act now", r"(?i)buy now", r"(?i)discount code",
    r"(?i)promo code", r"(?i)coupon", r"(?i)free shipping",
    r"(?i)your account will be closed", r"(?i)confirm your email",
    r"(?i)verify your email", r"(?i)email verification",
    r"(?i)thank you for subscribing", r"(?i)you are receiving",
    r"(?i)if you no longer wish", r"(?i)to opt out", r"(?i)opt out",
    r"(?i)advertisement", r"(?i)marketing", r"(?i)promotional",
    r"(?i)invoice|receipt|bill", r"(?i)order confirmation",
    r"(?i)payment received", r"(?i)thank you for your purchase",
    r"(?i)otp|one.time pass|驗證碼", r"(?i)password reset|重設密碼",
    r"(?i)sign in required", r"(?i)login attempt", r"(?i)security alert",
    r"(?i)Suspicious activity", r"(?i)login from new device",
    r"(?i)weekly digest", r"(?i)monthly digest", r"(?i)daily digest",
]

# 主旨關鍵字黑名單
SUBJECT_KEYWORD_DENYLIST = [
    r"(?i)newsletter", r"(?i)公告", r"(?i)行銷", r"(?i)廣告",
    r"(?i)優惠", r"(?i)折扣", r"(?i)promotion", r"(?i)offer",
    r"(?i)webinar", r"(?i)event reminder", r"(?i)會議邀請",
    r"(?i)meeting invite", r"(?i)calendar invite",
    r"(?i)notification", r"(?i)提醒", r"(?i)您有一個",
    r"(?i)新訂單", r"(?i)order confirmed", r"(?i)invoice",
    r"(?i)receipt", r"(?i)payment", r"(?i)帳單",
    r"(?i)verify|驗證", r"(?i)密碼", r"(?i)密碼",
    r"(?i)系統訊息", r"(?i)system message",
    r"(?i)auto-reply", r"(?i)自動回覆", r"(?i)out of office",
    r"(?i)平日您好", r"(?i)您好，感謝您的訂閱",
]

# 白名單關鍵字（出現這些關鍵鍵就直接通過）
BODY_KEYWORD_ALLOWLIST = [
    r"4-h", r"4h", r"youth summit", r"delegation", r"grasseping",
    r"invitation", r"letter of invitation", r"program",
    r"代表", r"草根", r"訪問", r"來訪", r"交流",
    r"registration", r"apply", r"application form",
    r"visa", r"護照", r"行程", r"itinerary",
    r"honor", r"award", r"recognition", r"表彰",
    r"collaboration", r"partnership", r"合作",
    r"international", r"global", r"world", r"世界",
    r"payment due", r"invoice", r"billing", r"帳單",
]

SUBJECT_KEYWORD_ALLOWLIST = [
    r"(?i)4-h", r"(?i)4h", r"(?i)invitation", r"(?i)delegate",
    r"(?i)代表", r"(?i)草根", r"(?i)summit", r"(?i)program",
    r"(?i)registration", r"(?i)application", r"(?i)來訪",
    r"(?i)visa", r"(?i)護照", r"(?i)行程",
    r"(?i)international", r"(?i)global",
]


@dataclass
class EmailCandidate:
    id: str
    subject: str
    sender: str
    sender_domain: str
    snippet: str
    date: str
    score: int          # 0-100，愈高愈可能是真人來信
    reject_reason: Optional[str] = None
    passed_filters: bool = False

    def to_dict(self):
        return asdict(self)


def run_gog(cmd: str) -> str:
    """執行 gog CLI，回傳 stdout"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[WARN] gog 執行失敗: {result.stderr.strip()}", file=sys.stderr)
        return "{}"
    return result.stdout


def parse_gmail_search(query: str = "is:unread -in:chats newer_than:7d", max_results: int = 50) -> list:
    """用 gog 搜尋 Gmail，回傳信件清單"""
    cmd = f'gog gmail search "{query}" --max {max_results} --json'
    output = run_gog(cmd)
    try:
        data = json.loads(output)
        if isinstance(data, dict) and "messages" in data:
            return data["messages"]
        elif isinstance(data, list):
            return data
        return []
    except json.JSONDecodeError:
        print(f"[WARN] gog JSON 解析失敗，原始輸出：{output[:200]}", file=sys.stderr)
        return []


def extract_domain(sender: str) -> str:
    """從寄件者抽網域"""
    m = re.search(r'@([a-zA-Z0-9.-]+)', sender)
    return m.group(1).lower() if m else ""


def calc_score(email: dict) -> tuple[int, Optional[str]]:
    """計算信件分數與排除原因，回傳 (score, reject_reason)"""
    subject = email.get("subject", "")
    sender = email.get("sender", email.get("from", ""))
    snippet = email.get("snippet", email.get("body", ""))
    sender_domain = extract_domain(sender)

    score = 50  # 基礎分
    reject_reason = None

    # ── 強排除規則（直接 0 分）──
    # 黑名單網域
    if any(bad in sender_domain for bad in DOMAIN_DENYLIST):
        return 0, f"黑名單網域 ({sender_domain})"

    # No-Reply 寄件者
    if re.match(r".*(no.reply|noreply|no-reply|donotreply|automated).*", sender.lower()):
        return 0, "No-Reply 寄件者"

    # ── 主旨黑名單（直接排除）──
    for pat in SUBJECT_KEYWORD_DENYLIST:
        if re.search(pat, subject):
            return 0, f"主旨含黑名單關鍵字 ({pat})"

    # ── 內文黑名單（直接排除）──
    for pat in BODY_KEYWORD_DENYLIST:
        if re.search(pat, snippet):
            return 0, f"內文含黑名單關鍵字"

    # ── 加分規則 ──
    # 白名單網域（常見國際組織）
    good_domains = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
                    "4-h.org", "fourh.org", "states4h.org", "mail.4-h.org"}
    if sender_domain in good_domains:
        score += 15
    elif sender_domain and "." in sender_domain:
        score += 10  # 有網域就算分

    # 白名單關鍵字
    for pat in BODY_KEYWORD_ALLOWLIST:
        if re.search(pat, snippet + " " + subject):
            score += 15
            break

    for pat in SUBJECT_KEYWORD_ALLOWLIST:
        if re.search(pat, subject):
            score += 10
            break

    # 真人風格指標
    if re.search(r'[a-zA-Z]{3,}\s+[a-zA-Z]{3,}', sender):  # 有全名
        score += 5
    if len(snippet) > 80:  # 不是短 snippet
        score += 5
    if not re.match(r'^(re:|fw:|fwd:)', subject.lower()):  # 非回覆
        score += 5
    else:
        score -= 10  # 回覆扣分

    # ── 弱排除規則（低於門檻才排除）──
    # 系統風格內文
    sys_patterns = [
        r"this email was sent", r"you are receiving this because",
        r"if you believe this was sent", r"click here to unsubscribe",
        r"to change your preferences", r"update your email preferences",
        r"view this email in your browser", r"why did i get this",
    ]
    for pat in sys_patterns:
        if re.search(pat, snippet.lower()):
            score -= 15

    return max(0, min(100, score)), reject_reason


def filter_emails(dry_run: bool = False, min_score: int = 40) -> list[EmailCandidate]:
    """
    主過濾流程：
    1. 抓取近 7 天未讀信件
    2. 計算每封信分數
    3. 回傳通過門檻的候選清單
    """
    print(f"[INFO] 抓取 Gmail 未讀信件（近7天）...", file=sys.stderr)
    emails = parse_gmail_search()

    if not emails:
        print("[INFO] 未找到未讀信件", file=sys.stderr)
        return []

    print(f"[INFO] 找到 {len(emails)} 封信，開始過濾...", file=sys.stderr)

    candidates = []
    for email in emails:
        score, reject_reason = calc_score(email)
        sender = email.get("sender", email.get("from", ""))
        domain = extract_domain(sender)

        candidate = EmailCandidate(
            id=email.get("id", ""),
            subject=email.get("subject", ""),
            sender=sender,
            sender_domain=domain,
            snippet=email.get("snippet", ""),
            date=email.get("date", email.get("timestamp", "")),
            score=score,
            reject_reason=reject_reason,
            passed_filters=score >= min_score,
        )
        candidates.append(candidate)

    # 排序：分數高的在前
    candidates.sort(key=lambda x: x.score, reverse=True)

    if dry_run:
        print("\n=== 過濾結果（Dry Run） ===")
        print(f"{'分數':<6} {'通過':<6} {'主旨':<40} {'寄件網域':<25} {'原因'}")
        print("-" * 110)
        for c in candidates:
            status = "✅" if c.passed_filters else "❌"
            reason = c.reject_reason or ""
            subj = c.subject[:38] if len(c.subject) > 38 else c.subject
            print(f"{c.score:<6} {status:<6} {subj:<40} {c.sender_domain:<25} {reason}")
        return []

    passed = [c for c in candidates if c.passed_filters]
    print(f"[INFO] 過濾後：{len(passed)}/{len(candidates)} 封通過（分數≥{min_score}）", file=sys.stderr)

    return passed


def main():
    parser = argparse.ArgumentParser(description="Gmail 外文來信 Prefilter")
    parser.add_argument("--dry-run", action="store_true", help="測試模式：顯示過濾邏輯，不輸出結果")
    parser.add_argument("--min-score", type=int, default=40, help="最低分數門檻（預設 40）")
    parser.add_argument("--max", type=int, default=50, help="最多抓取封信數（預設 50）")
    args = parser.parse_args()

    passed = filter_emails(dry_run=args.dry_run, min_score=args.min_score)

    if args.dry_run:
        return

    # 輸出 JSON（與 triage cron prompt 相容）
    result = {
        "candidates": [c.to_dict() for c in passed],
        "count": len(passed),
        "filter_version": "1.0.0",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
