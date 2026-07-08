# M130 Exec Plan - Product Workbench Dogfood

## 目标

为 M126-M129 Agent 工作台增加最终 dogfood gate，验证它是否中文、只读、安全、文档完整，并在完成后停止。

## 范围

- 新增 `product_workbench_dogfood.py` 和 API。
- 检查 M126-M129 工作台核心文件、路由、UI、安全边界、文档链。
- 不进入 M131，不 push。

## 验收

- `/product-workbench-dogfood` 返回 ready。
- M126-M130 文档链完整。
- full tests / quality / docs / Chinese UI / diff check 通过。

