# Fix Recovered Notes

一个用于管理和恢复 Trilium 笔记中被标记为 "recovered"的笔记的工具脚本。支持检查、批量复制、删除原始笔记以及清理冗余副本等多种操作模式，可帮助用户修复因同步或导入问题产生的孤立笔记树。

## 📖 功能特性

- 🔍 **检查模式**: 扫描标题包含特定关键词的笔记，自动添加 TODO 提醒
- 📋 **复制模式**: 递归复制整个笔记子树并保留所有属性和附件
- 🗑️ **删除模式**: 安全删除原始 recovered 笔记及其子树
- 🧹 **清理模式**: 删除带有复制标记的冗余副本
- 💾 **自动备份**: 在执行修改操作前自动创建数据库备份
- 🏷 **标签管理**: 自动为复制品添加"已修复 recovered 错误"标签以便识别
- ☂️ **防御性设计**: 循环引用检测、异常安全处理、临时文件清理

## ⚠️ 重要说明

**本工具仅用于恢复和整理 Trilium 中因数据问题产生的 recovered 笔记，请勿用于恶意删除或篡改您的笔记库。** 

使用前请务必：
1. 确认目标笔记确实是错误或冗余的 recovered 笔记
2. 完整阅读本文档中的参数说明和安全建议
3. 做好数据库备份

## 🛠️ 安装与配置

### 前置要求

- Python 3.7+ 
- Trilium Notes 服务运行中（支持 ETAPI）

### 依赖安装

```bash
pip install trilium-py python-dotenv
```

> **注意**: 如果遇到 `trilium-py` 相关问题请参考 [`trilium_py-README.md`](https://github.com/Nriver/trilium-py/blob/main/README.md) 获取详细文档。

### 环境配置

在项目根目录创建 `.env` 文件并配置以下环境变量：

```env
TRILIUM_SERVER=http://localhost:8080
TRILIUM_TOKEN=your_etapi_token_here
TITLE_PREFIX=recovered
```

**环境变量说明**:

| 变量名 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| `TRILIUM_SERVER` | ✅ | `http://localhost:8080` | Trilium 服务器地址（支持 HTTP/HTTPS） |
| `TRILIUM_TOKEN` | ✅ | - | ETAPI Token（必需，否则程序会退出） |
| `TITLE_PREFIX` | ❌ | `recovered` | 用于识别 recovered 笔记的标题前缀关键词 |

获取 ETAPI Token 的方法：在 Trilium 中进入设置 → API → 创建新的 ETAPI Token，复制显示的 Token。

---

## 📖 使用方法

### 基本语法

```bash
python3 FixRecoveredNotes.py [选项]
```

### 操作模式（互斥）

#### 🔍 检查模式（默认）

仅扫描并提示，不修改任何笔记：

```bash
python3 FixRecoveredNotes.py
# 或使用显式参数（与默认行为相同）
python3 FixRecoveredNotes.py --check-only
```

**作用**: 
- 统计标题包含 `recovered` 前缀的笔记数量
- 在今天的待办事项中添加提醒，标记需人工检查

#### 📋 复制模式

递归复制所有找到的 recovered 笔记及其子树（保留所有属性和附件），原笔记保持不变：

```bash
python3 FixRecoveredNotes.py --copy
```

**作用**:
1. 为每个原始笔记创建完整副本
2. 自动添加标签"已修复 recovered 错误"到复制品
3. **防重复机制**: 如果原标题已存在此标签，跳过该笔记避免重复复制

**示例**:
```bash
# 复制前（原笔记）:
recovered_note_001 (无保护标记)

# 复制后:
recovered_note_001 (原笔记保持不变)
├── recovered_note_001_副本 ("已修复 recovered 错误"标签)
    └── child_notes... (完整子树保持一致性)
```

#### 🗑️ 删除模式

安全删除所有原始 recovered 笔记（即未添加复制标记的）及其子树：

```bash
python3 FixRecoveredNotes.py --delete
```

**作用**:
1. 识别标题包含 `recovered` 前缀的所有笔记
2. 过滤掉已添加"已修复 recovered 错误"标签的副本
3. **仅删除原始笔记**，保留复制品以验证数据完整性

**安全特性**:
- ✅ 跳过受保护笔记 (`isProtected: true`)
- ✅ 跳过已有复制标记的笔记（防止误删）
- ✅ 每次删除前会打印日志信息便于确认

#### 🧹 清理模式

删除所有标题匹配且带有"已修复 recovered 错误"标签的复制品笔记，通常用于完成验证后的清理工作：

```bash
python3 FixRecoveredNotes.py --clean
```

**作用**:
- 查找原始 notes 标题集合
- 遍历所有带标记的副本，确认标题与任何原始笔记匹配
- 删除匹配的复制品（保留原始 recovered 笔记）

⚠️ **注意**: 此操作会永久删除带有"已修复 recovered 错误"标签的笔记子树，建议先在检查模式下预览。

---

### 通用参数

#### `--no-backup`

跳过数据库备份步骤：

```bash
python3 FixRecoveredNotes.py --copy --no-backup
```

**场景**: 在已知已有备份或测试环境中使用，常规操作建议保留备份功能。

---

## 🔧 完整工作流程示例

### 场景：批量恢复因同步中断产生的损坏笔记

假设你的 Trilium 中有以下 recovered 笔记：
```
📁 root
  ├── recovered note 1
  ├── recovered note 2
  └── note 3
```

**推荐操作顺序**:

#### Step 1: 检查模式（预览）

```bash
python3 FixRecoveredNotes.py --check-only
```

查看输出日志确认找到的笔记：
```
2026-03-16 10:30:00 - INFO - 找到 2 个匹配笔记，准备添加 TODO 提醒
2026-03-16 10:30:00 - INFO - 笔记标题 recovered note 1
2026-03-16 10:30:00 - INFO - 笔记标题 recovered note 2
2026-03-16 10:30:00 - INFO - ✅ 已添加 TODO: 检查 recovered note
```

#### Step 2: 备份 + 复制模式（修复）

```bash
python3 FixRecoveredNotes.py --copy
```

日志示例：
```
📊 执行复制模式...
💾 数据库备份成功，备份名称：BeforeAction_20260316_103500.db
👍 复制笔记：'recovered note 1' (原 ID: xxx) -> 新 ID: yyy
✅ 已删除原始笔记及其子树：recovered note 1
```

#### Step 3: 验证并清理（可选）

确认复制的笔记功能正常后，执行清理模式：
```bash
python3 FixRecoveredNotes.py --clean
```

---

## 🧩 内部工作原理

### 笔记复制流程

1. **获取原笔记元数据**: 标题、类型、MIME、父节点 ID、子树结构
2. **判断保护状态**: 跳过 `isProtected=true` 的笔记防止误操作
3. **内容处理**:
   - `image/file` 类型：提取附件到临时文件再创建
   - `text/code/mindMap` 等：直接获取内容 + 默认值填充（空内容时）
   - 其他类型：尝试获取，失败则记录警告并使用空策略
4. **创建新笔记**: 根据类型调用对应的 API (`create_image_note`, `create_note`)
5. **添加标签**: 为复制品标记"已修复 recovered 错误"便于后续识别
6. **属性复制**: 递归复制所有 `label`、自定义属性到副本
7. **附件处理**: 对非 image/file 类型，单独上传所有附属文件
8. **子树递归**: 依次处理每个子节点，保持层级结构完整


---

## 🐛 常见问题与故障排除

### Q1: 提示 "未提供 Trilium ETAPI token"

**原因**: 环境变量 `TRILIUM_TOKEN` 未设置或为空。

**解决方法**:
1. 检查 `.env` 文件是否存在且包含正确的 Token
2. 确认变量名拼写正确（区分大小写）：`TRILIUM_TOKEN` 不是 `token`
3. 如果是命令行运行，确保当前目录下的 `.env` 能被读取

```bash
# 验证环境变量是否加载
python3 -c "import os; print('TOKEN:', os.environ.get('TRILIUM_TOKEN', '未设置'))"
```

### Q2: 备份失败但程序继续执行

日志会显示：
```
数据库备份失败：[错误详细信息]
```

**处理方法**:
- 检查 Trilium 服务是否正常 (`http://localhost:8080/api/app`)
- 确认磁盘空间充足
- 手动在 Trilium Web 界面创建备份作为保底方案

### Q3: 删除/复制操作比预期慢

**可能原因**:
1. 大量附件需要下载上传（每个文件都要经过临时目录）
2. 笔记树层级深导致递归次数多
3. 网络延迟（如果 Trilium 是远程部署）

**建议**:
- 使用 `--no-backup` 跳过耗时步骤进行测试
- 观察日志中的进度提示，不要中断程序运行

### Q4: 某些图片附件复制失败

常见错误：
```
复制附件 [attachment_name] 失败：[异常信息]
```

**处理方法**:
1. 检查原笔记是否真的包含附加文件（有些 `image` 类型的内容可能直接内嵌）
2. 手动复制该单条笔记作为测试，排除批量操作的并发问题

### Q5: TODO 添加失败

日志显示：
```
添加 TODO 失败：[错误]
```

**可能原因**:
1. 今天的待办笔记不存在且无法自动创建
2. `ea.get_day_note` 或 `ea.add_todo` 方法在 `trilium-py` 版本中未实现
3. Trilium 数据库锁定（另一个人或程序正在操作）

**手动添加 TODO 的方法**:
```python
# 临时修改脚本添加硬编码日期
today = "2026-03-16"
ea.set_day_note(today, 
    ea.get_day_note(today) + "\n- [ ] 检查 recovered note")
```

---

## 🛡️ 安全建议

### ⚠️ 操作前必做清单

1. ✅ **完整备份数据库**: 在 Trilium Web 界面手动执行一次 `Create Backup`（与脚本自动备份独立）
2. ✅ **确认笔记内容**: 至少打开几条 recovered 笔记确认其确认为错误或冗余
3. ✅ **选择小样本测试**: 如果 recovered 笔记超过 100 条，建议先创建包含少量笔记的测试子树验证逻辑
4. ✅ **记录当前状态**: 复制日志输出到本地文件，便于问题追溯

### 🚫 禁止操作场景

- ❌ **不要直接运行 `--delete` 模式**：必须先通过 `--copy` 和 `--check-only` 验证
- ❌ **不要在数据库写入期间运行**: Trilium 正在备份/导入时暂停本工具
- ❌ **不要用于普通笔记整理**: 本脚本专为 recovered 异常笔记设计

---

## 📄 日志文件说明

程序会在当前目录生成 `duplicate_log.md` 记录所有操作详情：

```log
2026-03-16 10:30:00 - INFO - 检索到 5 个匹配笔记...
2026-03-16 10:30:01 - INFO - 🔍 检查循环引用: note_id_abc123 ✓
2026-03-16 10:30:02 - INFO - 🗂️ 创建副本 'test_note' → new_id_xyz789
2026-03-16 10:30:05 - ERROR - ⚠️ 附件 [image.png] 复制失败：[详细错误堆栈]
```

**日志字段说明**:
| Level | 含义 | 处理方式 |
|-------|------|----------|
| `INFO` | 正常操作记录 | 可忽略，仅用于进度追踪 |
| `WARNING` | 非致命异常（如附件缺失） | 检查后继续操作 |
| `ERROR` | 操作失败（如备份错误） | 暂停并检查日志全文 |

---

## 🤝 贡献与反馈

欢迎提交 Issue 或 Pull Request 改进本工具！常见问题请优先查看本文档的"常见问题"段落。
