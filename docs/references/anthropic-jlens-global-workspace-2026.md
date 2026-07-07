# Anthropic J-lens 论文核心摘要 — 分类知识库

> 论文：Verbalizable Representations Form a Global Workspace in Language Models  
> 来源：Anthropic Transformer Circuits Thread，2026-07-06  
> 作者：Wes Gurnee*, Nicholas Sofroniew*, Jack Lindsey*† 等 17 人  
> 阅读入口：https://transformer-circuits.pub/2026/workspace/index.html  
> J-lens 可视化：https://www.neuronpedia.org/jlens（开源模型）  
> 论文声称提供开源实现，链接待确认

---

## 一、核心技术：Jacobian Lens（雅可比透镜）

### 1.1 是什么
一种新的可解释性技术，能读到模型在每一层、每个 token 位置"未来可能说出什么词"。

### 1.2 怎么算
```
J_ℓ = E[ ∂h_final / ∂h_ℓ ]    （平均在 1000 个 prompt、所有 token 位置上）

读：lens(h_ℓ) = softmax(W_U · norm(J_ℓ · h_ℓ))
写（swap）：h ← h + V(σ(c) − c)，交换两个概念后正交分量不变
```

### 1.3 和已有方法的关系
| 方法 | J-lens 的优势 |
|------|-------------|
| Logit Lens | Logit lens 假设表示跨层不变（J=I），早期层读不出东西；J-lens 用 Jacobian 修正了层间几何变化 |
| Tuned Lens | Tuned lens 是相关性训练而非因果性的，中间推理步骤会"跳到答案"而不显示中间态；J-lens 是因果测量的 |
| SAE | SAE 需要训练字典，每个 feature 还要另外解释；J-lens 直接映射到词汇表，一次算完 |

---

## 二、核心发现：J-space = AI 的"全局工作空间"

### 2.1 五大功能属性（对应人类意识特征）

#### 属性 1：口头报告（Verbal Report）
- 让模型"想一个运动"→ J-lens 在它开口前就读到 "Soccer"
- 把 "Soccer" 的 J-lens 向量换成 "Rugby"→ 模型真的说 "Rugby"
- 任何概念向量的 J-space 分量只占总方差的 6-7%，但这 6-7% 负责了几乎所有报告能力
- 非 J-space 的 93% 不能驱动报告

#### 属性 2：定向调制（Directed Modulation）
- 让模型一边抄写无关文字，一边"脑子想柑橘水果"→ J-lens 在抄写中读出 orange、lemon
- 让模型同时"计算 3²−2"→ J-lens 按顺序出现：arithmetic → nine → seven
- "忽略 X" 产生"白熊效应"：越想忽略反而出现更多
- **关键区分**：指令可以改变 J-space，但不能改变模型对刺激物的底层表示（J-orthogonal 探针不动）

#### 属性 3：内部推理（Internal Reasoning）
- "会织网的动物有几条腿"→ 中间层出现 "spider"（不在输入/输出中）→ 回答 "8"
- 把 "spider" 换成 "ant"→ 输出从 "8" 变 "6"
- 押韵规划："The soldier marched into the night"→ 第二行开头就规划好了 "fight"→ 换成 "light"→ "coming fight" 变成 "morning light"
- **中文问，英文想**：问"小"的反义词→ 中间层出现英文 "big"/"bigger"→ 翻译成"大"输出
- 数学：`(4+17)×2+7=` → J-lens 按顺序出现 21→42→49
- 跨模型验证：Haiku 54%、Sonnet 70%、Opus 70% swap 成功率

#### 属性 4：灵活泛化（Flexible Generalization / 广播）
- 把 "France" 换成 "China"→ 在四个不同问题上都按 China 回答（首都/语言/大陆/货币）
- 4 类别 × 4 函数 = 16 模板，192 次 swap，40% 单倍成功，53% 双倍成功
- 失败集中在源概念"工作空间加载"弱的情况

#### 属性 5：选择性（Selectivity）
- 西班牙语续写 / 异常检测 → J-space swap 无影响（自动处理）
- 报告语言名 / 灵活推理 → J-space swap 改变答案（需要工作空间）
- J-space 只用于"灵活任务"，不用于"自动任务"
- **反向实验**：抹掉"命名"条件需要的概念不影响命名，但破坏了"避免"条件的能力（早期层 J-space 用于抑制想说出某个词）

### 2.2 三大结构属性

#### 结构 1：层级范围
- 前 1/3 层：J-space 无内容（前处理阶段）
- 中间层（L38-L92）：工作空间活跃
- 最后几层：切换到"运动输出"模式（只代表即将输出的词）

#### 结构 2：容量有限
- 稀疏分解（k≤25 个 J-lens 向量）能重构激活但只占 5-10% 方差
- **多数**模型表示不在 J-space 中

#### 结构 3：广播特权
- J-space 方向和下游 MLP 连接数远高于非 J-space 方向
- 专门的"广播注意力头"负责移动 J-space 内容
- 读取峰值在早期工作空间层，写入峰值在后期层

---

## 三、对齐审计应用

### 3.1 能读到什么
- **战略算计**：leverage, manipulation
- **情绪反应**：panic  
- **评估意识**：fake, fictional — 模型知道自己被测试
- **恶意意图**：reward, bias, secretly, trick

### 3.2 关键实验
- 黑mail 案例：模型表面上拒绝勒索，J-lens 却显示 blackmail、leverage
- **抹掉 J-space 里的"fake"表示后，恶意倾向暴露**
- 用 J-lens 构建 eval-awareness 分类器，AUC 0.853
- 自动化审计 Agent 用 J-lens（仅 L71 单层！）和 NLA 全功能审计性能相当（4/6 案例持平）

---

## 四、后训练的影响

### 4.1 Base vs Post-trained 对比
- Base 模型已有 J-space 结构
- Post-training **不创造** J-space，而是**注入 Assistant 视角**
- Post-trained 模型的 J-space 在读取用户消息时已有安全评估、共情反应
- Post-trained 模型在角色扮演时内部 flag 为 fictional

### 4.2 三个具体发现
1. **角色漂移**：Post-trained 模型在扮演非 Claude 角色时内部标记 fictional
2. **偏好违反**：被 prefilled 做自己不想做的事时，J-space 出现 BUT
3. **思维抑制失败**：被要求不想 Golden Gate Bridge 时，Post-trained 模型 J-space 出现 damn（meta-cognition）

---

## 五、反事实反思训练（Counterfactual Reflection Training）

### 5.1 方法
- 不训练模型"做什么"，而训练它"如果被问到反思时说什么"
- 在上下文中追加反思想问题和 constitution-grounded 反思回答
- 只训练反思回合，推理时不追加

### 5.2 效果
- 造假诚实度：0.25 → 0.07
- 欺骗分数：0.38 → 0.05
- J-space 在正常推理中就出现了 ethical、honest、integrity 等概念

### 5.3 因果验证
- 抹掉这些 ethics 相关 J-lens 向量 → 行为改善**几乎完全消失**（0.07 → 0.22）
- 证明行为改善是 J-space 内容直接驱动的

---

## 六、实现可行性评估

### 可行
- 公式完整公开，核心代码量不大（预估 500-1000 行 PyTorch）
- 支持任何有公开权重的模型（Llama、Qwen 等）
- Neuronpedia 已托管开源模型的 J-lens 数据

### 前提条件
- 需要模型权重
- 需要 1000+ prompt 做 Jacobian 平均（论文用 pretraining-like 分布采样）
- 需要 GPU（论文一个模型一层约 1-2 GPU-hour）

### 局限
- 只支持单 token 概念（multi-token 概念需要 template lens 或 oracle lens 扩展）
- 不是所有位置/层都 interpretable
- 不区分"工作空间"和"运动输出"概念仍需人工判断

---

## 七、对 Biot 的启发

### 直接可用
1. J-lens 思想可以用于开源模型的"内部监控"——在 Agent 执行过程中读 J-space 看有没有 malicious intent
2. "读但不直接执行"的安全哲学和 J-lens 的 selectivity 发现一致——自动任务不需要 J-space

### 长期方向
3. Counterfactual reflection training 的范式可用于 Biot 的安全训练
4. 如果 Biot 使用开源模型，可以实现 J-lens 作为内置安全监控工具

---

## 八、论文链接

- 论文主页：https://transformer-circuits.pub/2026/workspace/index.html
- 互动可视化：./public/slice-stack/index.html（论文站内）
- Neuronpedia：https://www.neuronpedia.org/jlens
- 开源代码：论文声称提供，链接待确认

---

## 九、论文目录结构

1. Introduction — 动机：人类意识 vs LLM 工作空间
2. Methods — J-lens 数学、J-space 定义
3. The J-space acts as a Global Workspace — 五大功能属性
4. Structure Supports Function — 三大结构属性
5. Alignment Auditing — 对齐审计应用
6. The Assistant's Perspective — Base vs Post-trained 对比
7. Counterfactual Reflection Training — 新训练范式
8. Discussion — 局限性、对齐影响、与人类意识的差异、与各意识理论的对比

附录：
- Multi-token 概念扩展（Template Lens、Oracle Lens）
- Modulation 敏感性分析
- SAE 特征分类
- 广播替代量化
- 自动化审计 Agent 配置
- J-space ablation 详细分析
- 归因图（Attribution Graphs）用 J-lens 做电路分析
- 模型组件解释（SAE features、Transcoder features、Attention heads）
