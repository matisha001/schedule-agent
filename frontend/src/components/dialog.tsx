/** 命令式对话框：替代 window.alert / window.confirm 的组件弹框。 */

import { createRoot, type Root } from "react-dom/client";
import { DialogHost, type DialogState } from "./ui";

type DialogOptions = {
  title?: string;
  okText?: string;
  cancelText?: string;
  danger?: boolean;
};

// 懒创建的宿主根节点与状态更新函数，保证模块级单例、任意组件可直接调用
let dialogRoot: Root | null = null;
let updateDialog: ((state: DialogState | null) => void) | null = null;
let pendingDialog: DialogState | null = null;

function ensureDialogHost() {
  if (!dialogRoot) {
    const host = document.createElement("div");
    document.body.appendChild(host);
    dialogRoot = createRoot(host);
    // 首次打开时把暂存状态作为 initial 传入，避免在 effect 中 setState
    dialogRoot.render(
      <DialogHost
        initial={pendingDialog}
        register={(fn) => {
          updateDialog = fn;
        }}
      />,
    );
    pendingDialog = null;
  }
}

function openDialog(state: DialogState) {
  if (updateDialog) {
    updateDialog(state);
  } else {
    // 宿主尚未挂载完成（首次调用），先暂存，随首次渲染消费
    pendingDialog = state;
    ensureDialogHost();
  }
}

/** 确认对话框：用户点确定返回 true，取消/遮罩/Esc 返回 false。 */
export function confirmDialog(
  message: string,
  options: DialogOptions = {},
): Promise<boolean> {
  return new Promise((resolve) => {
    openDialog({
      message,
      title: options.title ?? "请确认",
      okText: options.okText ?? "确定",
      cancelText: options.cancelText ?? "取消",
      danger: options.danger ?? false,
      resolve,
    });
  });
}

/** 信息提示对话框：只有确定按钮，关闭后 resolve。 */
export function alertDialog(
  message: string,
  options: DialogOptions = {},
): Promise<void> {
  return new Promise((resolve) => {
    openDialog({
      message,
      title: options.title ?? "提示",
      okText: options.okText ?? "确定",
      cancelText: null,
      danger: false,
      resolve: () => resolve(),
    });
  });
}
