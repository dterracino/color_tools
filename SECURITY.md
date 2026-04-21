# Security Policy

## Supported Versions

The following versions of `color-match-tools` are currently supported with security updates:

| Version | Supported |
| ------- | --------- |
| 6.x     | ✅ Yes    |
| < 6.0   | ❌ No     |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

If you discover a security vulnerability, please send an email to **<dterracino@gmail.com>**
with the subject line `[SECURITY] color-match-tools vulnerability`.

Include as much of the following information as possible to help understand and resolve the issue:

- A description of the vulnerability and its potential impact
- Steps to reproduce or proof-of-concept code
- The affected version(s)
- Any suggested mitigation or fix

You should receive an acknowledgement within **48 hours**. If you have not heard back
after 72 hours, please follow up to ensure your message was received.

## Disclosure Policy

- Vulnerabilities will be investigated promptly
- A fix will be developed and tested
- A security advisory and patched release will be published
- Credit will be given to the reporter (unless anonymity is requested)

We aim to resolve confirmed vulnerabilities within **30 days** of the initial report.

## Scope

This library is a pure Python color science toolkit with **no network functionality**
and **no external service calls**. The primary security considerations are:

- **Data integrity**: SHA-256 hash verification protects core color science constants
  and data files from tampering (run `python -m color_tools --verify-all`)
- **Dependency vulnerabilities**: Optional extras (`[image]`, `[interactive]`,
  `[logging]`) introduce third-party packages that may have their own advisories
- **Malicious data files**: Untrusted custom JSON data files (user-colors.json,
  user-filaments.json) are loaded and parsed — validate their source before use

## Out of Scope

- Vulnerabilities in optional dependencies (report those to their respective projects)
- Issues that require physical access to the system
- Social engineering attacks
