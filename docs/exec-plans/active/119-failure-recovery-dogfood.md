# M119 Exec Plan — 失败恢复复盘
评估6种失败场景（patch apply失败、test失败、permission denied、stale、timeout、interrupted）的恢复建议。复用M64 failure_classifier+M65 safe_retry_loop。不自动修复。
