"use client";

import {
  Children,
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type PointerEvent,
  type ReactNode,
  type RefObject,
} from "react";
import {
  applyCompactScrollAlign,
  type CompactScrollAlign,
} from "@/components/charts/chartScrollUtils";

interface ChartScrollAreaProps {
  children: ReactNode;
  expandedChildren?: ReactNode;
  chartTitle?: string;
  compactScrollAlign?: CompactScrollAlign;
  scrollKey?: number | string;
}

const CLICK_MOVE_THRESHOLD_PX = 8;

function useCompactScrollAlign(
  containerRef: RefObject<HTMLDivElement | null>,
  align: CompactScrollAlign,
  scrollKey: number | string | undefined,
  children: ReactNode,
): void {
  const childrenCount = Children.count(children);

  useLayoutEffect(() => {
    applyCompactScrollAlign(containerRef.current, align);
  }, [containerRef, align, scrollKey, childrenCount]);

  useLayoutEffect(() => {
    const element = containerRef.current;
    if (element === null) {
      return;
    }

    const observer = new ResizeObserver(() => {
      applyCompactScrollAlign(element, align);
    });
    observer.observe(element);

    return () => {
      observer.disconnect();
    };
  }, [containerRef, align, scrollKey, childrenCount]);
}

export function ChartScrollArea({
  children,
  expandedChildren,
  chartTitle,
  compactScrollAlign = "end",
  scrollKey,
}: ChartScrollAreaProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const pointerOriginRef = useRef<{ x: number; y: number } | null>(null);
  const [expanded, setExpanded] = useState(false);
  const close = useCallback(() => setExpanded(false), []);
  const expandLabel = chartTitle
    ? `Powiększ wykres: ${chartTitle}`
    : "Powiększ wykres";

  useCompactScrollAlign(
    scrollContainerRef,
    compactScrollAlign,
    scrollKey,
    children,
  );

  useEffect(() => {
    if (!expanded) {
      return;
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        close();
      }
    };

    document.addEventListener("keydown", onKeyDown);
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
    };
  }, [expanded, close]);

  const onPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    pointerOriginRef.current = { x: event.clientX, y: event.clientY };
  };

  const onPointerUp = (event: PointerEvent<HTMLDivElement>) => {
    const origin = pointerOriginRef.current;
    pointerOriginRef.current = null;
    if (origin === null) {
      return;
    }

    const movedX = Math.abs(event.clientX - origin.x);
    const movedY = Math.abs(event.clientY - origin.y);
    if (movedX <= CLICK_MOVE_THRESHOLD_PX && movedY <= CLICK_MOVE_THRESHOLD_PX) {
      setExpanded(true);
    }
  };

  const onPointerCancel = () => {
    pointerOriginRef.current = null;
  };

  return (
    <>
      <div className="group min-w-0 max-w-full">
        <div
          ref={scrollContainerRef}
          className="min-w-0 max-w-full cursor-zoom-in overflow-x-auto overscroll-x-contain touch-pan-x pb-2 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden"
          onPointerDown={onPointerDown}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerCancel}
          role="button"
          tabIndex={0}
          aria-label={expandLabel}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              setExpanded(true);
            }
          }}
        >
          {children}
        </div>
        <p className="text-center text-[10px] text-slate-500 opacity-70 transition group-hover:opacity-100 sm:opacity-0 sm:group-hover:opacity-100">
          Przesuń poziomo lub kliknij, aby powiększyć
        </p>
      </div>

      {expanded ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/90 p-4 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-label={chartTitle}
          onClick={close}
        >
          <div
            className="max-h-[90vh] w-full max-w-6xl overflow-auto rounded-xl border border-slate-600 bg-slate-900 p-6 shadow-2xl"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="mb-4 flex items-center justify-between gap-4">
              {chartTitle ? (
                <h3 className="text-base font-semibold text-white">
                  {chartTitle}
                </h3>
              ) : (
                <span />
              )}
              <button
                type="button"
                onClick={close}
                className="rounded-md px-3 py-1 text-sm text-slate-400 transition hover:bg-slate-800 hover:text-white"
                aria-label="Zamknij"
              >
                Zamknij ✕
              </button>
            </div>
            <div className="w-full min-w-0 overflow-x-auto pb-2">
              {expandedChildren ?? children}
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
