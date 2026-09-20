/** 展示格式化：状态文案 / 时间 / 枚举标签。 */

export function formatDateTime(value?: string | null): string {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function formatDate(value?: string | null): string {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export const teamModeLabel = (mode: number) => (mode === 2 ? "个人赛" : "团队赛");
export const registMethodLabel = (method: number) =>
  method === 2 ? "选手自主报名" : "办赛者代报名";

/** 状态徽章颜色（Tailwind 类） */
export function statusColor(status: number, kind: "tournament" | "team" | "schedule"): string {
  const palette: Record<number, string> = {
    0: "bg-gray-100 text-gray-600 border-gray-200",
    1: "bg-blue-50 text-blue-600 border-blue-200",
    2: "bg-amber-50 text-amber-600 border-amber-200",
    3: "bg-red-50 text-red-600 border-red-200",
    4: "bg-emerald-50 text-emerald-600 border-emerald-200",
  };
  if (kind === "team" && status === 3) return "bg-gray-100 text-gray-500 border-gray-200";
  return palette[status] ?? "bg-gray-100 text-gray-600 border-gray-200";
}

export function playerStatusLabel(status: string): string {
  return status === "AGREED" ? "已同意" : status === "REJECTED" ? "已拒绝" : "待确认";
}
