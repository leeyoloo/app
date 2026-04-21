# Miuix Notes & Todo App

一个基于 Flutter 开发的 Miuix 风格应用，集成了待办事项、笔记、便签和日记功能。

## 功能特点

- **待办事项**：添加、编辑、删除待办任务，标记完成状态
- **笔记**：创建、编辑、删除笔记，支持标题和内容
- **便签**：添加、删除便签，支持多种颜色分类
- **日记**：记录每日日记，按日期查看

## 技术栈

- Flutter 3.0+
- Dart
- Provider (状态管理)
- Sqflite (本地存储)
- Hive (轻量级存储)
- Flutter Slidable (滑动操作)
- Intl (日期格式化)

## 项目结构

```
lib/
├── main.dart                 # 应用入口
├── views/
│   ├── home_view.dart        # 主页面，包含底部导航栏
│   ├── todo_view.dart        # 待办事项页面
│   ├── notes_view.dart       # 笔记页面
│   ├── memos_view.dart       # 便签页面
│   └── diary_view.dart       # 日记页面
├── models/                   # 数据模型
├── widgets/                  # 自定义组件
├── services/                 # 服务类
└── utils/                    # 工具类
assets/
├── icons/                    # 图标资源
└── images/                   # 图片资源
```

## 安装与运行

1. 确保你已经安装了 Flutter SDK
2. 克隆项目到本地
3. 运行以下命令安装依赖：
   ```bash
   flutter pub get
   ```
4. 运行应用：
   ```bash
   flutter run
   ```

## 设计风格

应用采用 Miuix 风格设计，具有以下特点：
- 简洁的白色背景
- 蓝色主题色
- 卡片式布局
- 流畅的动画效果
- 直观的用户界面

## 未来计划

- 添加数据持久化存储
- 实现云同步功能
- 添加更多主题选项
- 支持图片和附件
- 实现搜索功能

## 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目！
