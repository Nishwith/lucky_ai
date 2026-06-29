import { useEffect } from "react";
import { useLucky } from "../context/LuckyContext";
import { SystemMetrics } from "../types";

export const useSystemMetrics = (intervalMs: number = 3000) => {
  const { setMetrics, systemState } = useLucky();

  useEffect(() => {
    if (systemState === "ERROR") return;

    const fetchMetrics = async () => {
      try {
        const r = await fetch("http://localhost:8000/api/system/metrics");
        if (r.ok) {
          const data: SystemMetrics = await r.json();
          setMetrics(data);
        }
      } catch (err) {
        console.error("Failed to poll system metrics", err);
      }
    };

    fetchMetrics();

    const t = setInterval(fetchMetrics, intervalMs);
    return () => clearInterval(t);
  }, [setMetrics, systemState, intervalMs]);
};
