# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of AutoCron seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### Please Do Not:

- Open a public GitHub issue
- Disclose the vulnerability publicly before we've had a chance to address it

### Please Do:

1. **Email us directly** at: mdshoaibuddinchanda@gmail.com
2. **Include the following information:**
   - Type of vulnerability
   - Full paths of source file(s) related to the vulnerability
   - Location of the affected source code (tag/branch/commit or direct URL)
   - Step-by-step instructions to reproduce the issue
   - Proof-of-concept or exploit code (if possible)
   - Impact of the vulnerability
   - Your suggestions for mitigation (if any)

### What to Expect:

- **Acknowledgment**: We will acknowledge receipt of your vulnerability report within 48 hours
- **Assessment**: We will assess the vulnerability and determine its impact
- **Timeline**: We will provide an estimated timeline for a fix
- **Updates**: We will keep you informed of our progress
- **Credit**: We will credit you for the discovery (unless you prefer to remain anonymous)
- **Disclosure**: Once the vulnerability is fixed, we will coordinate public disclosure

### Security Update Process:

1. Vulnerability is reported and confirmed
2. Fix is developed and tested
3. Security advisory is drafted
4. Patch is released
5. Security advisory is published
6. CVE is requested (if applicable)

## Security Best Practices

When using AutoCron:

### 1. Credentials Management

- **Never** hardcode credentials in scripts or configuration files
- Use environment variables for sensitive data
- Use a secrets management system (e.g., AWS Secrets Manager, HashiCorp Vault)

```python
import os

email_config = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'from_email': os.environ.get('EMAIL_FROM'),
    'to_email': os.environ.get('EMAIL_TO'),
    'password': os.environ.get('EMAIL_PASSWORD')
}
```

### 2. Script Execution

- Validate and sanitize all script paths
- Use absolute paths when possible
- Set appropriate file permissions
- Run with least privilege necessary

```python
import os

script_path = os.path.abspath(user_provided_path)
if not script_path.startswith('/safe/directory/'):
    raise ValueError("Invalid script path")
```

### 3. Input Validation

- Validate all user inputs
- Sanitize task names and descriptions
- Validate cron expressions
- Check file paths before execution

### 4. Logging

- Don't log sensitive information
- Sanitize logs before storage
- Rotate and secure log files
- Monitor logs for suspicious activity

### 5. Network Security

- Use TLS for email notifications
- Validate SSL certificates
- Use secure SMTP configurations
- Implement rate limiting

### 6. System Security

- Keep AutoCron updated
- Review scheduled tasks regularly
- Audit task execution logs
- Monitor system resources

## Known Security Considerations

### OS-Level Scheduling

AutoCron can integrate with OS-level schedulers (cron, Task Scheduler):

- Tasks run with user privileges
- Review scheduled tasks regularly
- Secure crontab/Task Scheduler access
- Monitor for unauthorized task modifications

### Email Notifications

Email notifications require SMTP credentials:

- Use app-specific passwords
- Enable 2FA on email accounts
- Rotate credentials regularly
- Monitor for unauthorized access

### Script Execution

AutoCron executes Python scripts:

- Review scripts before scheduling
- Use code signing when possible
- Implement script whitelisting
- Monitor script modifications

## Security Advisories

Security advisories will be published:

- GitHub Security Advisories
- Project documentation
- Mailing list (if subscribed)
- Twitter/social media

## Compliance

AutoCron strives to follow:

- OWASP Top 10 guidelines
- CWE/SANS Top 25
- Python security best practices
- Industry-standard security practices

## Contact

For security concerns, contact:
- Email: mdshoaibuddinchanda@gmail.com
- PGP Key: [Contact for PGP key]

For general questions:
- GitHub Issues: https://github.com/mdshoaibuddinchanda/autocron/issues
- GitHub Discussions: https://github.com/mdshoaibuddinchanda/autocron/discussions

---

**Thank you for helping keep AutoCron and our users safe!**
