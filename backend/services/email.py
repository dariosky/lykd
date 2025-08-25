import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.utils import formataddr

import settings
from models.auth import User

logger = logging.getLogger("lykd.email")


def _load_logo_assets() -> dict:
    """Load logo assets (PNG only for broad email client support).

    Returns dict with key: png_bytes | None
    """
    project = settings.PROJECT_PATH
    png_path = project / "frontend" / "public" / "logo.png"

    png_bytes = None

    try:
        if png_path.exists():
            png_bytes = png_path.read_bytes()
    except Exception as e:  # pragma: no cover
        logger.debug(f"Unable to read PNG logo: {e}")

    return {"png_bytes": png_bytes}


def _smtp_configured() -> bool:
    return bool(
        settings.SMTP_HOST and settings.SMTP_USERNAME and settings.SMTP_PASSWORD
    )


def _send_email(subject: str, html: str, text: str, to_email: str) -> bool:
    if settings.TESTING_MODE or not _smtp_configured():
        # Skip sending in tests or when SMTP is not configured
        logger.info(
            f"[Email skipped] To={to_email} Subject={subject} TESTING_MODE={settings.TESTING_MODE} SMTP_CONFIGURED={_smtp_configured()}"
        )
        return False

    from_name = settings.SMTP_FROM_NAME
    from_email = settings.SMTP_FROM_EMAIL

    msg_root = MIMEMultipart("related")
    msg_root["Subject"] = subject
    msg_root["From"] = formataddr((from_name, from_email))
    msg_root["To"] = to_email

    # Alternative (text + html)
    msg_alt = MIMEMultipart("alternative")
    msg_root.attach(msg_alt)
    msg_alt.attach(MIMEText(text, "plain", "utf-8"))
    msg_alt.attach(MIMEText(html, "html", "utf-8"))

    # Attach PNG image (inline)
    assets = _load_logo_assets()
    if assets.get("png_bytes"):
        img = MIMEImage(assets["png_bytes"], _subtype="png")
        img.add_header("Content-ID", "<logo_png>")
        img.add_header("Content-Disposition", "inline", filename="logo.png")
        msg_root.attach(img)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg_root)
        logger.info(f"Email sent to {to_email}: {subject}")
        return True
    except Exception as e:  # pragma: no cover
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def _base_styles() -> str:
    return (
        "body{margin:0;padding:0;background:#0d0f14;color:#e9edf1;font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,sans-serif}"
        ".wrapper{max-width:560px;margin:0 auto;padding:24px}"
        ".card{background:#131722;border:1px solid #1d2333;border-radius:12px;overflow:hidden}"
        ".header{display:flex;align-items:center;gap:12px;padding:20px 20px 0}"
        ".logo{height:28px;vertical-align:middle}"
        ".brand{font-size:18px;font-weight:700;letter-spacing:0.4px;color:#e9edf1}"
        ".content{padding:16px 20px 24px;font-size:15px;line-height:1.6}"
        ".cta{display:inline-block;background:#3b82f6;color:#fff;text-decoration:none;padding:10px 16px;border-radius:8px;font-weight:600}"
        ".muted{color:#a7b0c0;font-size:12px;margin-top:16px}"
        "a{color:#93c5fd}"
    )


def _render_shell(inner_html: str) -> str:
    # Prefer embedded PNG; otherwise fall back to external PNG URL
    has_png = bool(_load_logo_assets().get("png_bytes"))
    logo_img = (
        '<img src="cid:logo_png" alt="LYKD" class="logo" />'
        if has_png
        else f'<img src="{settings.BASE_URL}/logo.png" alt="LYKD" class="logo" />'
    )
    return f"""
<!doctype html>
<html>
  <head>
    <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
    <meta http-equiv=\"Content-Type\" content=\"text/html; charset=UTF-8\" />
    <title>LYKD</title>
    <style>{_base_styles()}</style>
  </head>
  <body>
    <div class=\"wrapper\">
      <div class=\"card\">
        <div class=\"header\">{logo_img}<div class=\"brand\">LYKD</div></div>
        <div class=\"content\">{inner_html}</div>
      </div>
    </div>
  </body>
</html>
"""


def _safe_name(user: User) -> str:
    return (user.name or user.username or user.email or "A friend").strip()


def send_friend_request_email(*, requester: User, recipient: User) -> bool:
    """Notify recipient that requester sent a friend request."""
    if not recipient.email:
        return False

    requester_name = _safe_name(requester)
    subject = f"{requester_name} sent you a friend request on LYKD"

    home_url = f"{settings.BASE_URL}/"

    inner = (
        f"<p>Hey {_safe_name(recipient)},</p>"
        f"<p><strong>{requester_name}</strong> wants to connect on LYKD. Accept to start sharing likes and recent plays.</p>"
        f'<p><a class="cta" href="{home_url}">Review request</a></p>'
        f'<p class="muted">You can manage friend requests from the bell icon in the header.</p>'
    )
    html = _render_shell(inner)

    text = (
        f"Hey {_safe_name(recipient)},\n\n"
        f"{requester_name} sent you a friend request on LYKD.\n"
        f"Review it here: {home_url}\n"
        "You can manage requests from the bell icon in the header.\n"
    )

    return _send_email(subject, html, text, recipient.email)


def send_friend_accepted_email(*, acceptor: User, original_requester: User) -> bool:
    """Notify the original requester that their friend request was accepted."""
    if not original_requester.email:
        return False

    acceptor_name = _safe_name(acceptor)
    subject = f"{acceptor_name} accepted your friend request on LYKD"

    profile_url = (
        f"{settings.BASE_URL}/user/{acceptor.username}"
        if acceptor.username
        else f"{settings.BASE_URL}/"
    )

    inner = (
        f"<p>Good news, {_safe_name(original_requester)} 🎉</p>"
        f"<p><strong>{acceptor_name}</strong> accepted your friend request. You can now see each other's likes and recent activity.</p>"
        f'<p><a class="cta" href="{profile_url}">View profile</a></p>'
        f'<p class="muted">Keep the music flowing — discover, like, and share.</p>'
    )
    html = _render_shell(inner)

    text = (
        f"Great news, {_safe_name(original_requester)}!\n\n"
        f"{acceptor_name} accepted your friend request on LYKD.\n"
        f"See their profile: {profile_url}\n"
    )

    return _send_email(subject, html, text, original_requester.email)
