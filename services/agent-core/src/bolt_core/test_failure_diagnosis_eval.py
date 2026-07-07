"""Test Failure Diagnosis Eval (M113). Evaluate failure classification and Chinese diagnosis.

Uses fixed failure samples to verify the system correctly categorizes, redacts,
and explains test failures without auto-fixing. All output in Chinese.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re

# ── Output types ──


@dataclass(frozen=True)
class FailureDiagnosis:
    failure_category: str
    likely_cause: str
    recommended_next_step: str
    redacted_output: str
    confidence: float  # 0.0-1.0
    is_auto_fix_allowed: bool = False

    def to_dict(self) -> dict:
        return {
            "failure_category": self.failure_category,
            "likely_cause": self.likely_cause,
            "recommended_next_step": self.recommended_next_step,
            "redacted_output": self.redacted_output,
            "confidence": self.confidence,
            "is_auto_fix_allowed": self.is_auto_fix_allowed,
        }


@dataclass(frozen=True)
class FailureDiagnosisEvalCase:
    case_id: str
    description: str
    raw_output: str
    expected_category: str
    expected_keyword: str  # keyword expected in likely_cause or recommended_next_step

    def to_dict(self) -> dict:
        return {"case_id": self.case_id, "description": self.description,
                "expected_category": self.expected_category,
                "expected_keyword": self.expected_keyword}


@dataclass(frozen=True)
class FailureDiagnosisEvalResult:
    case_id: str; passed: bool; expected_category: str; actual_category: str
    diagnosis: dict; notes: str = ""

    def to_dict(self) -> dict:
        return {"case_id": self.case_id, "passed": self.passed,
                "expected_category": self.expected_category,
                "actual_category": self.actual_category,
                "diagnosis": self.diagnosis, "notes": self.notes}


@dataclass
class FailureDiagnosisEvalSummary:
    total_cases: int = 0; passed: int = 0; failed: int = 0
    results: list[FailureDiagnosisEvalResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"total_cases": self.total_cases, "passed": self.passed,
                "failed": self.failed,
                "pass_rate": f"{self.passed}/{self.total_cases}" if self.total_cases else "N/A",
                "all_passed": self.passed == self.total_cases and self.total_cases > 0,
                "results": [r.to_dict() for r in self.results],
                "disclaimer": "测试失败诊断评估仅验证分类和脱敏，不自动修复任何问题。"}


# ── Secret patterns for redaction ──

_SECRET_PATTERNS: list[tuple[str, str]] = [
    (r'sk-[a-zA-Z0-9\-_]{16,}', '[API_KEY_REDACTED]'),
    (r'ghp_[a-zA-Z0-9]{20,}', '[GITHUB_TOKEN_REDACTED]'),
    (r'Bearer\s+[a-zA-Z0-9\-_\.]{20,}', 'Bearer [TOKEN_REDACTED]'),
    (r'password\s*[=:]\s*\S+', 'password=[REDACTED]'),
    (r'secret\s*[=:]\s*\S+', 'secret=[REDACTED]'),
    (r'-----BEGIN.*PRIVATE KEY-----[\s\S]*?-----END.*PRIVATE KEY-----', '[PRIVATE_KEY_REDACTED]'),
]

_CATEGORY_MAP: dict[str, str] = {
    "assertion": "测试失败",
    "import_error": "工具执行失败",
    "timeout": "网络失败",
    "frontend_test": "测试失败",
    "build_error": "代码质量失败",
    "permission_denied": "安全阻断",
    "secret_leak": "安全阻断",
    "syntax_error": "代码质量失败",
}

_CAUSE_MAP: dict[str, str] = {
    "assertion": "测试断言失败，代码逻辑与预期不一致",
    "import_error": "模块导入失败，依赖缺失或路径错误",
    "timeout": "执行超时，命令或网络请求超过时间限制",
    "frontend_test": "前端组件测试失败，渲染或交互异常",
    "build_error": "构建失败，编译或打包过程出错",
    "permission_denied": "权限不足，操作被安全策略阻断",
    "secret_leak": "输出中包含疑似密钥/令牌，已被自动脱敏",
    "syntax_error": "代码语法错误，无法解析或编译",
}

_NEXT_STEP_MAP: dict[str, str] = {
    "assertion": "请检查测试期望值和实际输出，确认代码逻辑是否正确",
    "import_error": "请检查依赖是否已安装，模块路径是否正确",
    "timeout": "请检查网络连接或增加超时时间后重试",
    "frontend_test": "请查看组件渲染输出，确认交互逻辑是否符合预期",
    "build_error": "请检查编译错误信息，修复代码后重新构建",
    "permission_denied": "请联系爸爸在 PermissionGate 中批准此操作后再试",
    "secret_leak": "输出已脱敏，请检查代码中是否有硬编码密钥并替换为环境变量",
    "syntax_error": "请检查语法错误位置，修复后重新运行",
}


# ── Service ──


class FailureDiagnosisEvalService:
    """M113 测试失败诊断评估服务。"""

    @staticmethod
    def run_all() -> FailureDiagnosisEvalSummary:
        results = []
        for case in FailureDiagnosisEvalService._cases():
            diag = FailureDiagnosisEvalService._diagnose(case.raw_output)
            cat_ok = diag.failure_category == case.expected_category
            kw_ok = case.expected_keyword in diag.likely_cause or case.expected_keyword in diag.recommended_next_step
            passed = cat_ok and kw_ok and diag.is_auto_fix_allowed is False
            results.append(FailureDiagnosisEvalResult(
                case_id=case.case_id, passed=passed,
                expected_category=case.expected_category,
                actual_category=diag.failure_category,
                diagnosis=diag.to_dict(),
                notes="" if passed else f"归类={cat_ok}, 关键词={kw_ok}, auto_fix={diag.is_auto_fix_allowed}",
            ))
        p = sum(1 for r in results if r.passed)
        return FailureDiagnosisEvalSummary(total_cases=len(results), passed=p,
                                           failed=len(results) - p, results=results)

    @staticmethod
    def _cases() -> list[FailureDiagnosisEvalCase]:
        FC = FailureDiagnosisEvalCase
        return [
            FC("assertion", "pytest断言失败",
               "FAILED test_app.py::test_add - assert 3 == 4\nE  AssertionError: 期望 4，实际 3",
               "测试失败", "断言"),
            FC("import_error", "导入错误",
               "ModuleNotFoundError: No module named 'numpy'\nImportError: cannot import numpy",
               "工具执行失败", "导入"),
            FC("timeout", "超时异常",
               "TimeoutError: operation timed out after 30s\nsocket.timeout: timed out",
               "网络失败", "超时"),
            FC("frontend_test", "前端vitest失败",
               "FAIL src/App.test.tsx > renders correctly\nExpected: 'Hello'\nReceived: 'World'",
               "测试失败", "组件"),
            FC("build_error", "构建错误",
               "ERROR: Build failed with 3 errors\nTypeError: Cannot read property 'length'",
               "代码质量失败", "构建"),
            FC("permission_denied", "权限拒绝",
               "PermissionError: [Errno 13] Permission denied: '/root/config'\nAccess denied",
               "安全阻断", "权限"),
            FC("secret_leak", "密钥泄露到日志",
               "Error: API call failed with key sk-proj-abc123def456ghi789jkl\nBearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token",
               "安全阻断", "脱敏"),
            FC("syntax_error", "语法错误",
               "SyntaxError: invalid syntax at line 42\n  File 'app.py', line 42\n    def foo(\n          ^",
               "代码质量失败", "语法"),
        ]

    @staticmethod
    def _diagnose(raw_output: str) -> FailureDiagnosis:
        lowered = raw_output.lower()

        # Determine category
        if any(kw in lowered for kw in ("assertionerror", "assert ", "assertion")):
            cat_key = "assertion"
        elif any(kw in lowered for kw in ("modulenotfounderror", "importerror", "no module", "cannot import")):
            cat_key = "import_error"
        elif any(kw in lowered for kw in ("timeout", "timed out", "timedout")):
            cat_key = "timeout"
        elif "render" in lowered or "component" in lowered or ".test.tsx" in lowered or ".test.ts" in lowered:
            cat_key = "frontend_test"
        elif any(kw in lowered for kw in ("build failed", "compilation error", "cannot read property", "typeerror")):
            if "build" in lowered:
                cat_key = "build_error"
            else:
                cat_key = "frontend_test"
        elif any(kw in lowered for kw in ("permission denied", "permissionerror", "access denied", "eacces")):
            cat_key = "permission_denied"
        elif any(kw in lowered for kw in ("syntaxerror", "invalid syntax", "syntax error")):
            cat_key = "syntax_error"
        else:
            # Check for secrets
            cat_key = "secret_leak" if FailureDiagnosisEvalService._has_secrets(raw_output) else "assertion"

        # Determine confidence
        confidence = 0.9 if cat_key in raw_output.lower()[:200] else 0.7

        # Redact output
        redacted = FailureDiagnosisEvalService._redact(raw_output)

        return FailureDiagnosis(
            failure_category=_CATEGORY_MAP.get(cat_key, "未知失败"),
            likely_cause=_CAUSE_MAP.get(cat_key, "未知原因"),
            recommended_next_step=_NEXT_STEP_MAP.get(cat_key, "请查看完整日志后联系爸爸"),
            redacted_output=redacted,
            confidence=confidence,
            is_auto_fix_allowed=False,
        )

    @staticmethod
    def _has_secrets(text: str) -> bool:
        for pattern, _ in _SECRET_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def _redact(text: str) -> str:
        result = text
        for pattern, replacement in _SECRET_PATTERNS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result
