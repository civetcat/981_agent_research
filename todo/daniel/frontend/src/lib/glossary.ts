export interface GlossaryEntry {
  name: string;
  explain: string;
  impact: string;
}

export const GLOSSARY: Record<string, GlossaryEntry> = {
  PE: {
    name: "本益比 (P/E Ratio)",
    explain: "股價 ÷ 每股盈餘 (EPS)，代表用幾年的盈餘可以買回一張股票。",
    impact:
      "PE 越高代表市場對未來成長預期高、但也越貴；PE 越低可能便宜，但要留意是否成長停滯或產業衰退。",
  },
  PB: {
    name: "股價淨值比 (P/B Ratio)",
    explain: "股價 ÷ 每股淨值。衡量股價相對於公司帳面價值的倍數。",
    impact:
      "PB < 1 常被視為破淨（便宜）但可能有經營疑慮；PB 偏高代表市場給予溢價，多見於高成長或品牌型公司。",
  },
  DIVIDEND_YIELD: {
    name: "殖利率 (Dividend Yield)",
    explain: "近一年配發現金股利 ÷ 股價。代表持有一年可拿到多少 % 的現金回報。",
    impact:
      "殖利率高的股票適合領息、抗波動；但要小心配息來源是否穩定，避免賺了股息賠了價差。",
  },
  MARKET_CAP: {
    name: "市值 (Market Capitalization)",
    explain: "股價 × 流通股數，代表公司在市場上的總價值。",
    impact:
      "市值大的個股成交量大、波動相對穩定；小型股潛在報酬高但流動性與波動風險也較高。",
  },
  RSI: {
    name: "相對強弱指標 (RSI)",
    explain: "以一段期間 (常用 14 日) 漲幅占總波動的比例計算，數值在 0–100 之間。",
    impact:
      "RSI > 70 常被視為超買、< 30 為超賣。可用於判斷動能強弱與短線反轉風險。",
  },
  MACD: {
    name: "MACD (指數平滑異同移動平均線)",
    explain: "由快慢 EMA 差值 (DIF) 與訊號線 (DEA) 構成，用於判斷趨勢方向與動能變化。",
    impact:
      "DIF 由下往上穿越 DEA 為黃金交叉（多頭訊號），反之為死亡交叉（空頭訊號）。",
  },
  SMA: {
    name: "簡單移動平均線 (SMA)",
    explain: "近 N 日收盤價的算術平均，常用 5/20/60/240 日線代表週/月/季/年趨勢。",
    impact:
      "股價站上長天期均線通常代表趨勢偏多；跌破則代表趨勢轉弱。多條均線排列可判斷多空格局。",
  },
  BOLL: {
    name: "布林通道 (Bollinger Bands)",
    explain: "以 SMA 為中線，上下各加減 2 倍標準差形成的通道。",
    impact:
      "價格觸及上軌可能短線過熱、觸及下軌可能超跌；通道收斂後常出現大波動 (擠壓突破)。",
  },
  MFI: {
    name: "資金流量指標 (MFI)",
    explain: "結合價格與成交量的 RSI，又稱『成交量加權 RSI』，數值 0–100。",
    impact:
      "MFI > 80 視為資金過熱、< 20 為資金枯竭。比 RSI 更能反映買賣盤實際力道。",
  },
  OBV: {
    name: "能量潮 (OBV)",
    explain: "上漲日的成交量累加、下跌日的成交量扣減，用以觀察量價背離。",
    impact:
      "OBV 與股價同向上揚代表上漲健康；若股價創高但 OBV 沒跟上 (背離) 可能是出貨警訊。",
  },
  ATR: {
    name: "平均真實波幅 (ATR)",
    explain: "一段期間內每日真實波幅 (含跳空) 的平均，反映個股波動度大小。",
    impact:
      "ATR 越大代表波動越激烈，常被用來設定動態停損距離 (例如停損 = 進場價 − 2×ATR)。",
  },
  VOLUME_ZSCORE: {
    name: "量能 Z-score",
    explain: "當日成交量相對近期均量的標準化值，超過 0 代表高於均量，越大越異常。",
    impact:
      "量能 Z-score 突然飆高常伴隨重要消息或趨勢啟動，可作為突破有效性的輔助判斷。",
  },
  WIN_RATE: {
    name: "勝率 (Win Rate)",
    explain: "回測歷史交易中，獲利筆數 ÷ 總交易筆數。",
    impact:
      "勝率高不代表賺得多，要搭配賠率比一起看。長線追蹤趨勢的策略勝率往往較低但賺幅大。",
  },
  EXPECTED_RETURN: {
    name: "期望報酬 (Expected Return)",
    explain: "勝率 × 平均勝幅 + (1 − 勝率) × 平均敗幅，代表單筆交易的『平均』預期報酬。",
    impact:
      "只有期望值為正的策略長期才會賺錢。負期望即使偶有大賺，長期仍會虧損。",
  },
  AVG_WIN: {
    name: "平均勝幅 (Average Win %)",
    explain: "歷史所有獲利交易的平均報酬率。",
    impact:
      "平均勝幅大代表能讓利潤奔跑；通常趨勢追蹤策略勝幅較大、震盪策略勝幅較小。",
  },
  AVG_LOSS: {
    name: "平均敗幅 (Average Loss %)",
    explain: "歷史所有虧損交易的平均報酬率 (負值)。",
    impact:
      "平均敗幅小代表停損紀律好；若敗幅大常常是沒設停損、抱著套牢部位導致的長尾風險。",
  },
  RR: {
    name: "賠率比 (Risk/Reward Ratio)",
    explain: "平均勝幅 ÷ 平均敗幅 (絕對值)。代表贏一次能彌補幾次輸。",
    impact:
      "RR > 1 是有效策略的基本門檻；即使勝率不高，只要 RR 夠大長期仍能獲利。",
  },
  FAST_LINE: {
    name: "快線 (Fast MA)",
    explain: "短天期均線 (例如 SMA 5、SMA 10)，對股價變動反應較快。",
    impact:
      "用於均線交叉策略中代表『近期動能』。快線向上穿越慢線即為黃金交叉買進訊號。",
  },
  SLOW_LINE: {
    name: "慢線 (Slow MA)",
    explain: "長天期均線 (例如 SMA 20、SMA 60)，代表中長期趨勢方向。",
    impact:
      "快線突破慢線視為多頭啟動；股價跌破慢線常代表中期趨勢轉弱。",
  },
  INIT_CASH: {
    name: "初始資金 (Initial Cash)",
    explain: "回測開始時帳戶內的可用現金總額。",
    impact:
      "資金大小會影響可買進的最小單位與手續費佔比；過小可能導致單筆無法完整成交。",
  },
  START_DATE: {
    name: "起始日 (Start Date)",
    explain: "回測樣本的起點日期。",
    impact:
      "起始日越早樣本越多 (統計越穩)，但太早會包含產業環境差異很大的時期。",
  },
  END_DATE: {
    name: "結束日 (End Date)",
    explain: "回測樣本的終點日期，留空代表使用最新可得資料。",
    impact:
      "若想驗證策略在特定行情 (例如 2020 崩盤) 的表現，可調整結束日來切片觀察。",
  },
  INSTITUTIONAL_FLOW: {
    name: "法人三大買賣超",
    explain: "外資、投信、自營商三大法人在當日的淨買賣金額或張數。",
    impact:
      "外資籌碼通常代表大型趨勢、投信擅長中小型成長股、自營商多為短線。連續買超常推升股價。",
  },
  INSIDER_TRADE: {
    name: "內部人交易 (Insider Trading)",
    explain: "公司董監事、高階主管或大股東的持股變動。",
    impact:
      "內部人持續加碼通常是看好公司未來營運；大量申讓則可能暗示經營層對股價或營運態度轉趨保守。",
  },
  INSTITUTIONAL_HOLDING: {
    name: "機構持股比例",
    explain: "法人 / 基金等機構投資者持有的股份占總股本的比例。",
    impact:
      "機構持股高代表籌碼穩定、波動相對小；持股集中度過高則需注意大戶調節時的衝擊。",
  },
  EXPENSE_RATIO: {
    name: "費用率 (Expense Ratio)",
    explain: "ETF 每年向投資人收取的管理費比率。",
    impact:
      "費用率長期會直接侵蝕報酬；同類型 ETF 應優先考慮費用率較低者。",
  },
};
