import { ReactNode, useEffect, useRef } from 'react';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  wide?: boolean;
}

export default function Modal({ open, onClose, title, children, wide }: ModalProps) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open) {
      el.showModal();
      requestAnimationFrame(() => {
        const auto = el.querySelector<HTMLElement>('[autofocus]');
        if (auto) {
          auto.focus();
        } else {
          const first = el.querySelector<HTMLElement>('input, textarea, select');
          first?.focus();
        }
      });
    } else {
      el.close();
    }
  }, [open]);

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      className={`rounded-lg shadow-xl backdrop:bg-black/50 p-0 border-0 w-full m-auto ${wide ? 'max-w-4xl' : 'max-w-lg'}`}
    >
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
          >
            &times;
          </button>
        </div>
        {children}
      </div>
    </dialog>
  );
}
