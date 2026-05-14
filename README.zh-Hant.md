# Codex QR Code Skill

這是一個給 Codex 使用的 `qr-code` skill。安裝後，當使用者需要手機掃描、網站連結、美術素材、demo 連結、分享頁面或 QR 碼時，Codex 可以自動調用這個 skill 產生 PNG 或 SVG QR code。

## 功能

- 本機生成，不依賴線上 QR 服務。
- 支援 PNG，適合預覽、社群貼文、截圖、一般分享。
- 支援 SVG，適合網站、印刷、設計工具。
- 支援 UTF-8，包括繁體中文文字與網址。
- 內建 QR version 選擇、Reed-Solomon 錯誤修正、mask 評分。
- `agents/openai.yaml` 已設定可隱式調用。

## 安裝

下載這個 repo 或 `dist/qr-code-skill.zip`，把裡面的 `qr-code` 資料夾放到 Codex skills 目錄：

```text
Windows: C:\Users\<你的帳號>\.codex\skills\qr-code
macOS/Linux: ~/.codex/skills/qr-code
```

安裝後重開 Codex。

## 使用方式

通常不需要打特殊指令，直接自然說就可以：

```text
生成 YouTube 的 QR code
幫這個網站做一個手機掃描連結
把這個 demo link 做成 QR
這個作品頁要放 QR 碼
```

如果想強制指定這個 skill：

```text
用 $qr-code 幫我生成 https://www.youtube.com/ 的 QR code
```

## 範例

內容：

```text
https://www.youtube.com/
```

輸出：

![YouTube QR code](examples/youtube-qrcode.png)

SVG 版本：[examples/youtube-qrcode.svg](examples/youtube-qrcode.svg)

## Skill 結構

```text
qr-code/
  SKILL.md
  agents/openai.yaml
  scripts/make_qr.py
```

也可以直接執行腳本：

```powershell
python .\qr-code\scripts\make_qr.py "https://www.youtube.com/" --output ".\youtube-qrcode.png" --error-correction Q --scale 12 --print-json
```

## 驗證

這個 skill 已用 Codex 的 `quick_validate.py` 驗證通過，也實際產生過 PNG / SVG，測試內容包含一般 URL、繁中 URL、繁中文字串。

## 授權

MIT
