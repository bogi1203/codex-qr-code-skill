# QR Code Skill for Codex

Generate accurate, phone-scannable QR codes from Codex whenever a website, link, artwork, demo, or shareable output needs mobile scanning.

This repository contains a Codex skill named `qr-code`. After installation, Codex can call it automatically when the user asks for a QR code or when Codex decides a phone-scannable link would be useful.

## Features

- Generates QR codes locally without online QR services.
- Supports PNG for previews, screenshots, social posts, and general sharing.
- Supports SVG for websites, print, and design tools.
- Supports UTF-8 payloads, including Traditional Chinese text and URLs.
- Includes deterministic QR generation with Reed-Solomon error correction and mask scoring.
- Designed for implicit Codex invocation through `agents/openai.yaml`.

## Install

Download this repository or `dist/qr-code-skill.zip`, then place the `qr-code` folder in your Codex skills directory:

```text
Windows: C:\Users\<you>\.codex\skills\qr-code
macOS/Linux: ~/.codex/skills/qr-code
```

Restart Codex after installing the skill.

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
