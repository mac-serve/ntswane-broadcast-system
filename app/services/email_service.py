import os
import requests

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
WEBSITE_URL = "https://ntswane.co.za"


def build_email_template(title, content):
    #formatted_content = content.replace("\n", "<br>")
    return f"""
    <html>
    <body style="margin:0; padding:0; background:#0f0f10; font-family:Arial, sans-serif;">

        <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f0f10; padding:30px 0;">
            <tr>
                <td align="center">

                    <table width="600" cellpadding="0" cellspacing="0" style="background:#1a1a1d; border-radius:12px; overflow:hidden; border:1px solid #2a2a2d;">

                        <!-- Header -->
                        <tr>
                            <td style="background:#111; padding:20px; text-align:center;">
                                <h2 style="color:#d4af37; margin:0;">Ntswane Village</h2>
                                <small style="color:#aaa;">Communication Platform</small>
                            </td>
                        </tr>

                        <!-- Body -->
                        <tr>
                            <td style="padding:30px; color:#f5f5f5;">
                                <h3 style="color:#f1d67a;">{title}</h3>

                                <p style="line-height:1.6; color:#ddd;">
                                    {content}
                                </p>

                                <!-- CTA -->
                                <div style="margin:30px 0; text-align:center;">
                                    <a href="{WEBSITE_URL}" 
                                       style="background:#d4af37; color:#111; padding:12px 20px; text-decoration:none; border-radius:6px; font-weight:bold;">
                                       View All Updates
                                    </a>
                                </div>

                                <p style="color:#bbb; font-size:14px;">
                                    For any questions, feel free to contact us.
                                </p>
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="background:#111; padding:20px; text-align:center; color:#999; font-size:13px;">

                                <!-- Logo -->
                                <div style="margin-bottom:10px;">
                                    <img src="https://www.ntswane.co.za/static/images/logo.jpg" width="60" alt="Ntswane Village" />
                                </div>

                                <strong style="color:#d4af37;">Ntswane Village</strong><br>
                                Email: info@ntswane.co.za<br>
                                Phone: +27 69 104 9451<br>
                                Website: <a href="{WEBSITE_URL}" style="color:#d4af37;">ntswane.co.za</a>

                                <p style="margin-top:10px; font-size:12px; color:#666;">
                                    © 2026 MAC-SERVER. All rights reserved.
                                </p>

                            </td>
                        </tr>

                    </table>

                </td>
            </tr>
        </table>

    </body>
    </html>
    """


def send_email_message(to_email, subject, message):
    try:
        if not to_email:
            return False, "Missing email"

        formatted_message = message.replace("\n", "<br>")
        html_content = build_email_template(subject, formatted_message)

        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": EMAIL_FROM,
                "to": [to_email],
                "subject": subject,
                "html": html_content
            }
        )

        if response.status_code in [200, 201]:
            response = response.json()
            #print(response)
            provider_message_id = response.get("id")
            #print(provider_message_id)
            return True, None, provider_message_id
        else:
            return False, response.text, None

    except Exception as e:
        print(str(e))
        return False, str(e), None

def send_admin_reset_email(to_email, reset_link):
    subject = "Reset Your Admin Password"

    message = f"""
    We received a request to reset your Ntswane admin portal password.

    Click the link below to reset your password:
    {reset_link}

    This link will expire in 1 hour.

    If you did not request this, you can ignore this email.
    """

    return send_email_message(to_email, subject, message)