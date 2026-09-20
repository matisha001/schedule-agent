/** 通用 UI 组件：Button / Input / Select / Textarea / Badge / Modal / Spinner / Empty / Field。 */

import { useEffect, type ReactNode, type SelectHTMLAttributes } from "react";
import { Loader2, X } from "lucide-react";
import { statusColor } from "../lib/format";

/* ---------- Button ---------- */
export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  className = "",
  children,
  ...rest
}: {
  variant?: "primary" | "secondary" | "danger" | "ghost" | "success";
  size?: "sm" | "md";
  loading?: boolean;
  className?: string;
  children: ReactNode;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const base =
    "inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed";
  const sizes = { sm: "px-2.5 py-1.5 text-xs", md: "px-4 py-2 text-sm" };
  const variants = {
    primary: "bg-blue-600 text-white hover:bg-blue-700",
    secondary: "border border-gray-300 bg-white text-gray-700 hover:bg-gray-50",
    danger: "bg-red-600 text-white hover:bg-red-700",
    success: "bg-emerald-600 text-white hover:bg-emerald-700",
    ghost: "text-gray-500 hover:bg-gray-100",
  };
  return (
    <button className={`${base} ${sizes[size]} ${variants[variant]} ${className}`} {...rest}>
      {loading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
      {children}
    </button>
  );
}

/* ---------- Input / Textarea / Select ---------- */
const fieldCls =
  "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm outline-none transition-colors placeholder:text-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:bg-gray-50";

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  const { className = "", ...rest } = props;
  return <input className={`${fieldCls} ${className}`} {...rest} />;
}

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const { className = "", ...rest } = props;
  return <textarea className={`${fieldCls} ${className}`} {...rest} />;
}

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  const { className = "", children, ...rest } = props;
  return (
    <select className={`${fieldCls} ${className}`} {...rest}>
      {children}
    </select>
  );
}

/* ---------- Badge ---------- */
export function Badge({
  label,
  status,
  kind = "tournament",
}: {
  label: string;
  status: number;
  kind?: "tournament" | "team" | "schedule";
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${statusColor(status, kind)}`}
    >
      {label}
    </span>
  );
}

/* ---------- Modal ---------- */
export function Modal({
  open,
  title,
  onClose,
  children,
  footer,
  width = "max-w-lg",
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  width?: string;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div
        className={`relative flex max-h-[90vh] w-full ${width} flex-col rounded-2xl bg-white shadow-xl dark:bg-gray-900`}
      >
        <div className="flex shrink-0 items-center justify-between border-b border-gray-100 px-5 py-4">
          <h3 className="text-base font-semibold text-gray-900">{title}</h3>
          <button onClick={onClose} className="rounded p-1 text-gray-400 hover:bg-gray-100">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">{children}</div>
        {footer && (
          <div className="flex shrink-0 justify-end gap-2 border-t border-gray-100 px-5 py-3">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

/* ---------- 其他 ---------- */
export function Spinner({ text = "加载中…" }: { text?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-sm text-gray-400">
      <Loader2 className="h-4 w-4 animate-spin" /> {text}
    </div>
  );
}

export function Empty({ text = "暂无数据" }: { text?: string }) {
  return <div className="py-12 text-center text-sm text-gray-400">{text}</div>;
}

export function Field({
  label,
  required,
  hint,
  children,
  className = "",
}: {
  label: string;
  required?: boolean;
  hint?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={className}>
      <label className="mb-1 block text-sm font-medium text-gray-700">
        {required && <span className="mr-0.5 text-red-500">*</span>}
        {label}
      </label>
      {children}
      {hint && <p className="mt-1 text-xs text-gray-400">{hint}</p>}
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
      {message}
    </div>
  );
}
