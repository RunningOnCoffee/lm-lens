import { useState, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';

export default function InfoTip({ text }) {
  const [pos, setPos] = useState(null);
  const iconRef = useRef(null);

  const show = useCallback(() => {
    const el = iconRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    setPos({
      top: rect.top - 8,
      left: rect.left + rect.width / 2,
    });
  }, []);

  const hide = useCallback(() => setPos(null), []);

  return (
    <span
      ref={iconRef}
      className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full bg-surface-600 text-gray-500 text-[9px] font-bold leading-none cursor-help"
      onMouseEnter={show}
      onMouseLeave={hide}
    >
      i
      {pos && createPortal(
        <span
          style={{
            position: 'fixed',
            top: pos.top,
            left: pos.left,
            transform: 'translate(-50%, -100%)',
          }}
          className="px-2.5 py-1.5 text-[11px] text-gray-300 bg-surface-700 border border-surface-600 rounded-lg shadow-lg w-64 z-[9999] leading-relaxed pointer-events-none"
        >
          {text}
        </span>,
        document.body,
      )}
    </span>
  );
}
