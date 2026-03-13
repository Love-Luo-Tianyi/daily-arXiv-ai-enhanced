#!/usr/bin/env python3
"""
每日邮件推送脚本 / Daily email notification script

功能说明 / Features:
- 向指定邮箱发送每日 arXiv 论文摘要通知 / Send daily arXiv paper summary notifications
- 邮件包含预览网站链接，提醒用户查看今日内容 / Email includes preview website link

必要的环境变量 / Required environment variables:
  SMTP_SERVER       - SMTP 服务器地址 / SMTP server hostname (e.g., smtp.gmail.com)
  SMTP_PORT         - SMTP 端口 / SMTP port (e.g., 587)
  SMTP_USERNAME     - SMTP 登录用户名 / SMTP login username
  SMTP_PASSWORD     - SMTP 登录密码 / SMTP login password (or app password)
  EMAIL_SENDER      - 发件人邮箱 / Sender email address
  EMAIL_RECIPIENTS  - 收件人邮箱，多个用逗号分隔 / Recipient emails, comma-separated
  GITHUB_PAGES_URL  - GitHub Pages 网站 URL / GitHub Pages website URL

可选的环境变量 / Optional environment variables:
  EMAIL_DATE        - 日期标题，默认为今日 / Date label, defaults to today
"""

import os
import sys
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def build_email_html(date_str: str, pages_url: str) -> str:
    """构建 HTML 邮件正文 / Build the HTML email body."""
    pages_url = pages_url.rstrip("/")
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Daily arXiv AI Enhanced - {date_str}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #f5f5f5;
      margin: 0;
      padding: 20px;
      color: #333;
    }}
    .container {{
      max-width: 600px;
      margin: 0 auto;
      background: #ffffff;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }}
    .header {{
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: #ffffff;
      padding: 32px 28px;
      text-align: center;
    }}
    .header h1 {{
      margin: 0 0 8px;
      font-size: 24px;
      font-weight: 700;
    }}
    .header p {{
      margin: 0;
      font-size: 14px;
      opacity: 0.85;
    }}
    .body {{
      padding: 32px 28px;
    }}
    .body p {{
      font-size: 15px;
      line-height: 1.7;
      margin: 0 0 16px;
    }}
    .cta {{
      text-align: center;
      margin: 28px 0;
    }}
    .cta a {{
      display: inline-block;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: #ffffff;
      text-decoration: none;
      padding: 14px 36px;
      border-radius: 8px;
      font-size: 16px;
      font-weight: 600;
      letter-spacing: 0.3px;
    }}
    .footer {{
      background: #f9f9f9;
      border-top: 1px solid #e8e8e8;
      padding: 18px 28px;
      text-align: center;
      font-size: 12px;
      color: #999;
    }}
    .footer a {{
      color: #667eea;
      text-decoration: none;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>📄 Daily arXiv AI Enhanced</h1>
      <p>{date_str} 的 AI 论文摘要已就绪 / Today's AI paper summaries are ready</p>
    </div>
    <div class="body">
      <p>您好！</p>
      <p>
        今日（<strong>{date_str}</strong>）的 arXiv 论文摘要已由 AI 处理完毕，
        涵盖最新的学术研究进展。点击下方按钮即可查看今日精选内容。
      </p>
      <p>
        Hello! Today's (<strong>{date_str}</strong>) arXiv paper summaries have been
        processed by AI. Click the button below to explore today's highlights.
      </p>
      <div class="cta">
        <a href="{pages_url}">🔍 查看今日论文摘要 / View Today's Summaries</a>
      </div>
      <p style="font-size:13px; color:#888;">
        若按钮无法点击，请复制以下链接到浏览器打开：<br>
        If the button does not work, copy this link into your browser:<br>
        <a href="{pages_url}" style="color:#667eea;">{pages_url}</a>
      </p>
    </div>
    <div class="footer">
      由 <a href="https://github.com/dw-dengwei/daily-arXiv-ai-enhanced">daily-arXiv-ai-enhanced</a> 自动发送 /
      Sent automatically by daily-arXiv-ai-enhanced
    </div>
  </div>
</body>
</html>"""


def build_email_text(date_str: str, pages_url: str) -> str:
    """构建纯文本邮件正文（备用）/ Build plain-text fallback email body."""
    return (
        f"Daily arXiv AI Enhanced - {date_str}\n"
        "\n"
        f"今日（{date_str}）的 arXiv 论文 AI 摘要已就绪，请点击链接查看：\n"
        f"Today's ({date_str}) arXiv paper AI summaries are ready. Visit:\n"
        "\n"
        f"{pages_url}\n"
        "\n"
        "---\n"
        "Sent by daily-arXiv-ai-enhanced"
    )


def send_notification(
    smtp_server: str,
    smtp_port: int,
    username: str,
    password: str,
    sender: str,
    recipients: list[str],
    date_str: str,
    pages_url: str,
) -> None:
    """发送通知邮件 / Send the notification email."""
    subject = f"📄 Daily arXiv AI Enhanced - {date_str} 论文摘要已就绪"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)

    text_part = MIMEText(build_email_text(date_str, pages_url), "plain", "utf-8")
    html_part = MIMEText(build_email_html(date_str, pages_url), "html", "utf-8")

    # 纯文本在前，HTML 在后（优先显示 HTML）
    # Plain text first, HTML last (clients prefer the last part)
    msg.attach(text_part)
    msg.attach(html_part)

    print(f"正在连接 SMTP 服务器 {smtp_server}:{smtp_port} / Connecting to {smtp_server}:{smtp_port} ...")
    with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(username, password)
        server.sendmail(sender, recipients, msg.as_string())
    print(f"✅ 邮件已成功发送至 {recipients} / Email sent successfully to {recipients}")


def main() -> None:
    required_vars = [
        "SMTP_SERVER",
        "SMTP_PORT",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "EMAIL_SENDER",
        "EMAIL_RECIPIENTS",
        "GITHUB_PAGES_URL",
    ]

    missing = [v for v in required_vars if not os.environ.get(v)]
    if missing:
        print(
            f"❌ 缺少必要的环境变量 / Missing required environment variables: {', '.join(missing)}",
            file=sys.stderr,
        )
        sys.exit(1)

    smtp_server = os.environ["SMTP_SERVER"]
    smtp_port = int(os.environ["SMTP_PORT"])
    username = os.environ["SMTP_USERNAME"]
    password = os.environ["SMTP_PASSWORD"]
    sender = os.environ["EMAIL_SENDER"]
    recipients = [r.strip() for r in os.environ["EMAIL_RECIPIENTS"].split(",") if r.strip()]
    pages_url = os.environ["GITHUB_PAGES_URL"]

    date_str = os.environ.get("EMAIL_DATE") or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if not recipients:
        print("❌ EMAIL_RECIPIENTS 中未找到有效邮箱 / No valid recipients found in EMAIL_RECIPIENTS", file=sys.stderr)
        sys.exit(1)

    print(f"📧 准备发送每日摘要邮件 ({date_str}) / Preparing daily summary email ({date_str})")
    print(f"   收件人 / Recipients: {recipients}")
    print(f"   网站链接 / Website URL: {pages_url}")

    send_notification(smtp_server, smtp_port, username, password, sender, recipients, date_str, pages_url)


if __name__ == "__main__":
    main()
