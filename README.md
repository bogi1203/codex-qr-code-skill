# QR Code Skill for Codex

[![Release](https://img.shields.io/github/v/release/bogi1203/codex-qr-code-skill?label=release)](https://github.com/bogi1203/codex-qr-code-skill/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Codex Skill](https://img.shields.io/badge/Codex-skill-blue)](qr-code/SKILL.md)

Offline QR code generator skill for OpenAI Codex. Generate accurate, phone-scannable QR codes as PNG or SVG whenever a website, link, artwork, demo, local preview, social post, or shareable output needs mobile scanning.

This repository contains a Codex skill named `qr-code`. After installation, Codex can call it automatically when the user asks for a QR code or when Codex decides a phone-scannable link would be useful.

## Download / Quick Install

**Paste this into Codex to install:**

```text
Use $skill-installer to install https://github.com/bogi1203/codex-qr-code-skill/tree/main/qr-code
```

**Download ZIP:** [qr-code-skill.zip](https://github.com/bogi1203/codex-qr-code-skill/releases/download/v0.1.0/qr-code-skill.zip)

**Windows PowerShell install:**

```powershell
$zip = Join-Path $env:TEMP "qr-code-skill.zip"
$skills = Join-Path $env:USERPROFILE ".codex\skills"
New-Item -ItemType Directory -Force $skills | Out-Null
Invoke-WebRequest -Uri "https://github.com/bogi1203/codex-qr-code-skill/releases/download/v0.1.0/qr-code-skill.zip" -OutFile $zip
Expand-Archive -Path $zip -DestinationPath $skills -Force
Remove-Item $zip
```

**macOS / Linux install:**

```bash
mkdir -p ~/.codex/skills
curl -L -o /tmp/qr-code-skill.zip "https://github.com/bogi1203/codex-qr-code-skill/releases/download/v0.1.0/qr-code-skill.zip"
unzip -o /tmp/qr-code-skill.zip -d ~/.codex/skills
rm /tmp/qr-code-skill.zip
```

Restart Codex after installing the skill.

## Keywords

Codex skill, OpenAI Codex skill, Codex QR code, QR code generator, qrcode generator, offline QR generator, phone scan link, mobile scanning, PNG QR code, SVG QR code, AI agent skill, agent workflow, shareable demo link, website QR code, design QR code.

## Best For

- Codex users who want automatic QR code generation during website, app, design, or launch workflows.
- Developers sharing demo links, preview URLs, local tunnel URLs, docs, dashboards, and landing pages.
- Designers and creators who need QR codes for posters, mockups, social images, printable assets, or client previews.
- AI agent workflows that should generate scannable phone links without relying on third-party QR websites.

## Features

- Generates QR codes locally without online QR services.
- Supports PNG for previews, screenshots, social posts, and general sharing.
- Supports SVG for websites, print, and design tools.
- Supports UTF-8 payloads, including Traditional Chinese text and URLs.
- Includes deterministic QR generation with Reed-Solomon error correction and mask scoring.
- Designed for implicit Codex invocation through `agents/openai.yaml`.

## Install

If you prefer manual installation, download this repository or `dist/qr-code-skill.zip`, then place the `qr-code` folder in your Codex skills directory:

```text
Windows: C:\Users\<you>\.codex\skills\qr-code
macOS/Linux: ~/.codex/skills/qr-code
```

## Usage

You usually do not need a command. After installation, ask naturally:

```text
Generate a QR code for my YouTube channel.
Make this website link scannable by phone.
Create a QR code for this demo URL.
這個網站幫我做成 QR 碼。
```

To force Codex to use this skill explicitly:

```text
Use $qr-code to generate a QR code for https://www.youtube.com/
```

## Share Blurb

Need a QR code inside Codex? `codex-qr-code-skill` is an offline OpenAI Codex skill that automatically generates phone-scannable PNG/SVG QR codes for websites, demos, artwork, social posts, and shareable links.

## Example

Payload:

```text
https://www.youtube.com/
```

Output:

![YouTube QR code](examples/youtube-qrcode.png)

SVG version: [examples/youtube-qrcode.svg](examples/youtube-qrcode.svg)

## Skill Contents

```text
qr-code/
  SKILL.md
  agents/openai.yaml
  scripts/make_qr.py
```

`scripts/make_qr.py` can also be run directly:

```powershell
python .\qr-code\scripts\make_qr.py "https://www.youtube.com/" --output ".\youtube-qrcode.png" --error-correction Q --scale 12 --print-json
```

## Validation

This skill was validated with Codex's `quick_validate.py` and tested by generating PNG and SVG QR codes for:

- normal URLs
- Traditional Chinese URL text
- Traditional Chinese plain text

## License

MIT
