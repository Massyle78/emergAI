import { useEffect, useRef, useState } from "react";

const BAR_COUNT = 24;
const FFT_SIZE = 256;
const REFRESH_MS = 50;

interface AudioVisualizerProps {
  stream: MediaStream | null;
  active: boolean;
}

/**
 * Real-time audio level bars using the Web Audio API.
 *
 * Connects an AnalyserNode to the stream and samples
 * frequency data at ~20 fps to drive a bar visualization.
 */
export function AudioVisualizer({ stream, active }: AudioVisualizerProps) {
  const [levels, setLevels] = useState<number[]>(() =>
    Array.from({ length: BAR_COUNT }, () => 0),
  );
  const ctxRef = useRef<AudioContext | null>(null);
  const rafRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!stream || !active) {
      setLevels(Array.from({ length: BAR_COUNT }, () => 0));
      return;
    }

    const audioCtx = new AudioContext();
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = FFT_SIZE;
    const source = audioCtx.createMediaStreamSource(stream);
    source.connect(analyser);
    ctxRef.current = audioCtx;

    const data = new Uint8Array(analyser.frequencyBinCount);

    rafRef.current = setInterval(() => {
      analyser.getByteFrequencyData(data);
      const step = Math.floor(data.length / BAR_COUNT);
      const bars = Array.from({ length: BAR_COUNT }, (_, i) => {
        const val = data[i * step] ?? 0;
        return val / 255;
      });
      setLevels(bars);
    }, REFRESH_MS);

    return () => {
      if (rafRef.current !== null) clearInterval(rafRef.current);
      void audioCtx.close();
    };
  }, [stream, active]);

  return (
    <div className="flex h-16 items-end justify-center gap-1">
      {levels.map((level, i) => (
        <div
          key={i}
          className="w-1.5 rounded-full bg-primary-500 transition-all duration-75"
          style={{ height: `${Math.max(8, level * 100)}%` }}
        />
      ))}
    </div>
  );
}
