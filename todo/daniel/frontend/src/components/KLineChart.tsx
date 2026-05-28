import { useEffect, useRef } from "react";
import {
  CandlestickData,
  ColorType,
  HistogramData,
  IChartApi,
  ISeriesApi,
  LineData,
  LineStyle,
  createChart,
} from "lightweight-charts";
import type { OHLCVRow } from "../api/client";

export type Overlay = {
  name: string;
  values: { date: string; value: number | null }[];
  color?: string;
};

interface Props {
  data: OHLCVRow[];
  overlays?: Overlay[];
  panes?: Array<"volume" | "macd" | "rsi">;
  height?: number;
}

const BG = "#0b0f17";
const GRID = "#1f2937";
const TEXT = "#cbd5e1";
const BORDER = "#374151";

const PALETTE = ["#fbbf24", "#60a5fa", "#a78bfa", "#f472b6", "#34d399"];

function commonOpts(width: number, height: number) {
  return {
    width,
    height,
    layout: { background: { type: ColorType.Solid, color: BG }, textColor: TEXT },
    grid: {
      vertLines: { color: GRID },
      horzLines: { color: GRID },
    },
    timeScale: { borderColor: BORDER, rightOffset: 6 },
    rightPriceScale: { borderColor: BORDER },
    crosshair: { mode: 0 },
  };
}

export default function KLineChart({ data, overlays = [], panes = [], height = 460 }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  // refs to all chart instances + their main series
  const chartsRef = useRef<IChartApi[]>([]);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const overlaysRef = useRef<ISeriesApi<"Line">[]>([]);
  const volRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const macdHistRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const macdLineRef = useRef<ISeriesApi<"Line"> | null>(null);
  const macdSignalRef = useRef<ISeriesApi<"Line"> | null>(null);
  const rsiRef = useRef<ISeriesApi<"Line"> | null>(null);

  // ---- create / destroy charts when panes change ----
  useEffect(() => {
    if (!containerRef.current) return;
    containerRef.current.innerHTML = ""; // clear previous

    const w = containerRef.current.clientWidth;
    const paneHeights: Record<string, number> = {
      main: height,
      volume: 100,
      macd: 130,
      rsi: 110,
    };

    const charts: IChartApi[] = [];
    const divs: HTMLDivElement[] = [];

    // helper to create a chart pane
    const mkPane = (h: number, label?: string) => {
      const wrap = document.createElement("div");
      wrap.style.position = "relative";
      wrap.style.width = "100%";
      if (label) {
        const tag = document.createElement("div");
        tag.textContent = label;
        tag.style.cssText =
          "position:absolute;top:6px;left:8px;z-index:1;font-size:11px;color:#9ca3af;background:rgba(11,15,23,0.7);padding:1px 6px;border-radius:4px;";
        wrap.appendChild(tag);
      }
      const inner = document.createElement("div");
      wrap.appendChild(inner);
      containerRef.current!.appendChild(wrap);
      divs.push(wrap);
      const c = createChart(inner, commonOpts(w, h));
      charts.push(c);
      return c;
    };

    const main = mkPane(paneHeights.main);
    candleRef.current = main.addCandlestickSeries({
      upColor: "#ef4444",
      downColor: "#10b981",
      borderUpColor: "#ef4444",
      borderDownColor: "#10b981",
      wickUpColor: "#ef4444",
      wickDownColor: "#10b981",
    });

    if (panes.includes("volume")) {
      const c = mkPane(paneHeights.volume, "成交量");
      volRef.current = c.addHistogramSeries({ priceFormat: { type: "volume" } });
    }
    if (panes.includes("macd")) {
      const c = mkPane(paneHeights.macd, "MACD");
      macdHistRef.current = c.addHistogramSeries({ priceLineVisible: false });
      macdLineRef.current = c.addLineSeries({
        color: "#fbbf24",
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      macdSignalRef.current = c.addLineSeries({
        color: "#60a5fa",
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
      });
    }
    if (panes.includes("rsi")) {
      const c = mkPane(paneHeights.rsi, "RSI 14");
      rsiRef.current = c.addLineSeries({
        color: "#a78bfa",
        lineWidth: 2,
        priceLineVisible: false,
      });
      // 30 / 70 reference lines
      rsiRef.current.createPriceLine({
        price: 70,
        color: "#ef4444",
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: "70",
      });
      rsiRef.current.createPriceLine({
        price: 30,
        color: "#10b981",
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: "30",
      });
    }

    chartsRef.current = charts;

    // sync time axis across all panes
    let syncing = false;
    const syncOthers = (src: IChartApi) => {
      if (syncing) return;
      syncing = true;
      const range = src.timeScale().getVisibleLogicalRange();
      if (range) {
        for (const c of charts) {
          if (c !== src) c.timeScale().setVisibleLogicalRange(range);
        }
      }
      syncing = false;
    };
    charts.forEach((c) =>
      c.timeScale().subscribeVisibleLogicalRangeChange(() => syncOthers(c))
    );

    const onResize = () => {
      const ww = containerRef.current?.clientWidth ?? w;
      charts.forEach((c, i) =>
        c.applyOptions({
          width: ww,
          height: i === 0 ? paneHeights.main : c.options().height,
        })
      );
    };
    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
      charts.forEach((c) => c.remove());
      chartsRef.current = [];
      candleRef.current = null;
      overlaysRef.current = [];
      volRef.current = null;
      macdHistRef.current = macdLineRef.current = macdSignalRef.current = null;
      rsiRef.current = null;
      divs.forEach((d) => d.remove());
    };
  }, [panes.join(","), height]);

  // ---- feed data ----
  useEffect(() => {
    if (!candleRef.current) return;

    const cs: CandlestickData[] = data
      .filter((d) => d.open != null && d.close != null)
      .map((d) => ({
        time: d.date,
        open: d.open!,
        high: d.high!,
        low: d.low!,
        close: d.close!,
      }));
    candleRef.current.setData(cs);

    if (volRef.current) {
      const vol: HistogramData[] = data
        .filter((d) => d.volume != null && d.close != null && d.open != null)
        .map((d) => ({
          time: d.date,
          value: d.volume!,
          color: d.close! >= d.open! ? "rgba(239,68,68,0.55)" : "rgba(16,185,129,0.55)",
        }));
      volRef.current.setData(vol);
    }

    if (macdHistRef.current && macdLineRef.current && macdSignalRef.current) {
      const hist: HistogramData[] = [];
      const macdLine: LineData[] = [];
      const sigLine: LineData[] = [];
      data.forEach((d: any) => {
        if (d.macd_hist != null) {
          hist.push({
            time: d.date,
            value: d.macd_hist,
            color: d.macd_hist >= 0 ? "rgba(239,68,68,0.6)" : "rgba(16,185,129,0.6)",
          });
        }
        if (d.macd != null) macdLine.push({ time: d.date, value: d.macd });
        if (d.macd_signal != null) sigLine.push({ time: d.date, value: d.macd_signal });
      });
      macdHistRef.current.setData(hist);
      macdLineRef.current.setData(macdLine);
      macdSignalRef.current.setData(sigLine);
    }

    if (rsiRef.current) {
      const ld: LineData[] = data
        .filter((d: any) => d.rsi_14 != null)
        .map((d: any) => ({ time: d.date, value: d.rsi_14 }));
      rsiRef.current.setData(ld);
    }

    if (chartsRef.current[0] && cs.length > 0) {
      chartsRef.current[0].timeScale().fitContent();
    }
  }, [data]);

  // ---- overlays on main chart ----
  useEffect(() => {
    if (!chartsRef.current[0] || !candleRef.current) return;
    const main = chartsRef.current[0];

    overlaysRef.current.forEach((s) => main.removeSeries(s));
    overlaysRef.current = [];

    overlays.forEach((o, i) => {
      const series = main.addLineSeries({
        color: o.color || PALETTE[i % PALETTE.length],
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      const ld: LineData[] = o.values
        .filter((v) => v.value != null)
        .map((v) => ({ time: v.date, value: v.value as number }));
      series.setData(ld);
      overlaysRef.current.push(series);
    });
  }, [overlays]);

  return <div ref={containerRef} className="w-full space-y-1" />;
}
