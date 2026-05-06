# TOEIC 智能背单词 App

基于 Python + KivyMD 的 Android 背单词应用，支持 SRS 记忆算法、TOEIC 语境例句、离线 TTS 发音。

## 核心功能

- **智能复习 (SRS)**：熟悉/模糊/不知道三级反馈 + 二次确认防误触
- **TOEIC 语境例句**：每个单词自动生成商务/职场场景例句
- **离线 TTS**：点击播放美式发音，无需联网
- **学习看板**：7日学习量与遗忘率统计
- **生词本**：自动收集"不知道"单词，支持导出 txt
- **深色模式**：一键切换

## 获取 APK（推荐方式）

### 方法 1：GitHub Actions 自动打包（免费，什么都不用装）

1. **在 GitHub 创建新仓库**
   - 登录 github.com → 点击 New repository → 命名为 `toeic-vocab`
   - 设置为 Public（Private 仓库 Actions 有时限）

2. **上传本项目代码**
   - 下载/复制 `E:\toeic_vocab_app\` 下的全部文件
   - 在仓库页面点击 "uploading an existing file" → 拖拽上传所有文件
   - Commit changes

3. **等待自动打包**
   - 进入仓库 → Actions 标签页
   - 看到 `Build TOEIC Vocab APK` workflow 正在运行（约 10-15 分钟）
   - 绿色 ✅ 完成后，进入页面底部 Artifacts 下载 APK
   - 或者等 workflow 自动发布到 Releases 页面

4. **安装到手机**
   - 下载 `TOEIC背单词-APK.zip`，解压得到 `.apk`
   - 传到安卓手机，允许"未知来源"安装，直接安装

### 方法 2：Pydroid 3 直接运行（最快，无需打包）

1. 安卓手机安装 **Pydroid 3**（Google Play 或应用市场搜索）
2. 打开 Pydroid 3 → 菜单 → Terminal
3. 安装依赖：
   ```bash
   pip install kivy kivymd
   ```
4. 把 `main.py` 和 `assets/vocabulary.json` 复制到手机
5. 在 Pydroid 3 里打开 `main.py`，点击黄色运行按钮

## 项目结构

```
toeic_vocab_app/
├── main.py                  # App 入口
├── buildozer.spec           # Android 打包配置
├── build_vocab.py           # OCR 词库提取脚本
├── build.bat                # Windows 桌面版打包（备用）
├── requirements.txt         # Python 依赖
├── assets/
│   ├── vocabulary.json      # 完整词库（GitHub Actions 自动生成）
│   └── vocabulary_sample.json  # 预置样本（60词）
├── pdf_pages/               # 14页 PDF 图片（用于 OCR）
└── .github/workflows/
    └── build-apk.yml        # GitHub Actions 自动打包配置
```

## 词库说明

内置词库来自你提供的 **14页扫描版 PDF**（TOEIC 阅读核心词汇）。

- **GitHub Actions 打包时**：自动用 PaddleOCR 识别全部14页图片，生成完整 `vocabulary.json` 打包进 APK
- **本地运行**：如果未 OCR，使用 `vocabulary_sample.json`（60词样本）

如需自己扩展词库，在电脑上运行：

```bash
pip install paddlepaddle paddleocr pymupdf pillow
python build_vocab.py
```

这会读取 `pdf_pages/*.png`，输出 `assets/vocabulary.json`。

## SRS 复习间隔

| 反馈 | 行为 | 下次复习 |
|---|---|---|
| 不知道 | 进入生词本 + Learning | 5 分钟后 |
| 模糊 | 进入 Learning | 5 分钟后 |
| 熟悉 (新词) | 进 Review | 1 天后 |
| 熟悉 (Learning) | Learning 步进 | 30 分钟 → 1 天后进 Review |
| 熟悉 (Review) | 拉长间隔 | 1→3→7→14→30 天 |

## 技术栈

- **UI**：KivyMD（Material Design for Kivy）
- **数据库**：SQLite3（内置，零配置）
- **TTS**：plyer.tts（Android 原生发音）
- **打包**：Buildozer / python-for-android

## 常见问题

**Q: GitHub Actions 打包失败？**
A: 检查 `buildozer.spec` 里的 `android.api` 是否 ≤ GitHub 环境支持版本。如失败，尝试修改 `android.api = 31`。

**Q: APK 安装后闪退？**
A: 可能是词库 JSON 过大导致内存不足。尝试减少 `vocabulary.json` 词汇量，或分批次导入。

**Q: 发音没声音？**
A: 确保手机没有静音，且系统 TTS 引擎已安装中文/英文语音包。

**Q: 想自己修改代码再打包？**
A: 修改 `main.py` 后 push 到 GitHub，Actions 会自动重新打包。

---

_祝 TOEIC 备考顺利！_
