---
name: code-review-go-cpp-p0p3
description: Reviews Go and C/C++ code changes with a P0-P3 severity rubric and concise bullet output in Traditional Chinese. Use when the user asks for code review, PR review, change review, or requests feedback on diffs/patches for Go/C++ projects, focusing on correctness, reliability, readability, performance. 常見觸發：幫我審查 / 看一下這個 diff / 幫我檢視 / 這個 PR / 幫我看一下這份改動 / 風險等級 / 嚴重度 / P0 P1 P2 P3 / 有沒有問題 / 這樣改 OK 嗎。
---

# Code Review（Go / C++，P0–P3）

## 目標

- **以變更為中心**：針對 diff/PR 內容找出風險與可改進點
- **輸出要可行動**：每點都要能直接改、或能明確驗證
- **分級一致**：用 **P0–P3** 表達優先順序

## 嚴重度定義（P0–P3）

- **P0（必修）**：會造成錯誤行為、資料毀損、安全風險、死鎖/崩潰、嚴重相容性問題，或上線後高機率事故
- **P1（高優先）**：不穩定/錯誤處理不足、邊界條件漏掉、明顯效能或資源問題、可維護性大幅下降
- **P2（建議）**：可讀性/一致性/測試不足、可簡化、可更清楚的命名與抽象、可觀測性補強
- **P3（可選）**：風格/小幅重構/非關鍵優化（不影響正確性）

## Review 前置步驟（先做再評）

1. **鎖定範圍**：本次變更「想解決什麼」與「影響哪些路徑」
2. **列出風險點**：資料流、錯誤處理、併發、資源生命週期、ABI/API 變更
3. **找既有實作**：若專案已經有同類 helper/模式，優先沿用（避免重複輪子）

## 輸出格式（固定模板）

請用以下結構輸出（繁體中文、條列、短句可執行）：

```markdown
## 結論
- 風險等級：P?（最高者）
- 建議：可合併 / 需修正後再合併 / 不建議合併

## P0
- （若無則省略本節）

## P1
- ...

## P2
- ...

## P3
- ...

## 建議測試/驗證
- 單元測試：...
- 整合/手動：...
- 回歸風險：...
```

## 通用檢查重點（每次都要過一遍）

- **正確性**
  - 是否涵蓋空值/空集合/溢位/錯誤碼/EOF/逾時等邊界條件
  - 是否有不一致的資料狀態（半更新、缺乏交易性/回滾）
- **穩定性/錯誤處理**
  - 錯誤是否被吞掉、是否有足夠的上下文（context）讓問題可定位
  - 重試/退避策略是否可能放大問題（thundering herd、無上限重試）
- **可讀性/可維護性**
  - 命名是否表達「意圖」；函式是否單一職責；重複邏輯是否該抽出
  - public API 變更是否有清楚的遷移路徑
- **效能/資源**
  - 不必要的配置/拷貝、熱路徑中的字串拼接、N+1、同步鎖競爭
  - 資源釋放是否明確（file/socket/mutex/thread）

## Go 專項檢查

- **錯誤處理**
  - `error` 是否往上回傳並保留上下文（wrap），避免只回傳原始錯誤字串
  - sentinel error 與 `errors.Is/As` 使用是否正確
- **context**
  - 是否把 `context.Context` 往下傳；是否正確處理取消/逾時
- **併發**
  - goroutine 是否可能 leak（未關閉 channel、無退出條件）
  - data race 風險（共享 map/slice、非同步回呼）
- **效能習慣**
  - 熱路徑避免 `fmt.Sprintf`/反射；必要時預先配置容量（`make(..., 0, n)`）

## C/C++ 專項檢查

- **生命週期與資源管理**
  - 優先 RAII（`std::unique_ptr`/`std::shared_ptr`/scope guard），避免裸 `new/delete`
  - 是否可能 double-free、use-after-free、dangling reference
- **例外/錯誤通道一致**
  - 專案若不用 exception，新增程式碼是否仍遵循 return-code/`std::optional`/`expected` 模式
- **字串/緩衝區**
  - `snprintf`/buffer 長度、`std::string_view` 的生命週期、C API 互動的 NUL 結尾
- **併發**
  - lock 順序、鎖粒度、避免在持鎖下做 I/O 或可能阻塞的呼叫
- **效能**
  - 不必要拷貝（pass-by-value）、可否用 move、容器 reallocation、避免在迴圈內做昂貴操作

## 什麼情況要升級嚴重度

- **有機率造成 crash / deadlock / data corruption**：至少 P0
- **錯誤處理缺失會導致無法定位/恢復**：至少 P1
- **可讀性問題導致容易誤用 API**：至少 P1 或 P2（視影響範圍）

