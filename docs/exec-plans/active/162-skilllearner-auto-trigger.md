# M162 SkillLearner Auto Trigger 执行计划

## 目标

让 SkillLearner 可以根据失败记忆主动扫描重复失败模式，并生成改进提案。

## 验收标准

- SkillLearner 只生成提案，不自动修改业务代码。
- 同类失败模式可以被识别并汇总。
- 桌面面板中文展示扫描结果和提案。
- targeted tests、desktop tests、quality、Chinese UI、diff check 通过。

## 风险

- SkillLearner 不得越权改代码或自动批准。
- 提案必须保留人工审查边界。
