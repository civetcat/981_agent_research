---
name: validation-notes-generic-zh
description: Writes production or release validation notes in Traditional Chinese using a fixed five-field format (Type/Description/Issue ID/Validation/Check List). Use when the user needs QA-facing validation steps between two tags/branches, 驗證筆記, release validation, or structured verification docs — after you point the skill to your project's existing note template file.
---

# 驗證筆記（繁體中文，通用版）

## 目標

依**你專案既有的 validation notes 版型**，產出「base tag vs 目前 branch」的驗證文件。只描述**改了什麼、要怎麼驗**，不解釋實作細節。

## 開工前要釐清（資訊不足就先問）

1. **Base**：比較基準 tag / branch
2. **Head**：目前要驗證或發版的 branch
3. **版本字串**：要寫進標頭的顯示名稱
4. **格式參照檔**：repo 內「已存在」的驗證筆記或 release note 範例路徑；**沿用同一套版型，不要自創**
5. **產出份量**：完整版（每主題一條）還是精簡版（合併為少數條）

## 固定版型（每條建議五欄）

```
Type: Fix | Enhancement | New Feature
Description: <一句話說明改了什麼，給 QA 看>
Issue ID: <issue 追蹤編號，或 commit hash>
Validation:
  1. <測試步驟 1>
  2. <測試步驟 2>
Check List:
  [ ] <驗證項 1>
  [ ] <驗證項 2>
```

- **Type**：只從專案約定的分類選，不要自創。
- **Validation**：可觀察的預期結果，避免「請查閱程式碼」。
- **Check List**：對應 Validation 的可勾選項。

## 建議流程

1. `git log --oneline base..head`，把 commits 依主題合併成 3–8 條（不要一 commit 一條）。
2. 讀「格式參照檔」，沿用欄位順序與縮排。
3. 日期若未知，占位 `YYYY/MM/DD`，由發版當天再填。

## 寫 Validation 步驟的原則

- **從使用者視角**：按哪個按鈕、下哪個指令、看什麼畫面／log。
- **可重現**：不依賴無法描述的內部狀態。
- **避免太技術**：少貼 internal class 名，除非 QA 真的需要。

## 不做的事

- 不自創版型（除非專案還沒有任何範本，這時要先和使用者定稿版型）。
- 不把所有 commit 一對一列出。
- 不寫無法由 QA 驗證的「純內部重構」條目（除非專案流程要求）。

## 輸出

- 在對話中用 markdown code block 包著文字即可；或寫入專案約定的 `release/` 目錄檔名規則。
- 回覆中列出：條目數、仍待使用者填的欄位（日期、issue id 等）。
