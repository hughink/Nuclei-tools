import sys
import os
import uuid
import yaml
import shlex
import shutil
import hashlib
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget, QTableWidgetItem,
                             QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QPlainTextEdit,
                             QMessageBox, QLineEdit, QSplitter, QMenu, QCheckBox, QLabel,
                             QInputDialog, QHeaderView, QFileDialog, QDialog, QListWidget,
                             QFrame, QScrollArea, QListWidgetItem, QDialogButtonBox, QAbstractItemView, QTextEdit,
                             QProgressDialog)
from PyQt5.QtGui import (QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QPainter,
                         QFontMetrics, QPalette, QTextFormat, QTextCursor)
from PyQt5.QtCore import Qt, QRegExp, QSize, QRect, QPoint, QThread, pyqtSignal


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class NucleiPOCHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlightingRules = []

        # 定义颜色常量，方便主题切换
        BLUE = "#1E90FF"  # 关键字颜色
        GREEN = "#32CD32"  # 值颜色
        RED = "#B22222"  # 注释颜色
        ORANGE = "#FFA500"  # 特殊关键字颜色
        PURPLE = "#9400D3"  # 匹配器颜色

        # 关键字格式（蓝色加粗）
        keyFormat = QTextCharFormat()
        keyFormat.setForeground(QColor(BLUE))
        keyFormat.setFontWeight(QFont.Bold)

        # 特殊关键字格式（橙色加粗）
        specialKeyFormat = QTextCharFormat()
        specialKeyFormat.setForeground(QColor(ORANGE))
        specialKeyFormat.setFontWeight(QFont.Bold)

        # 值格式（绿色）
        valueFormat = QTextCharFormat()
        valueFormat.setForeground(QColor(GREEN))

        # 注释格式（红色）
        commentFormat = QTextCharFormat()
        commentFormat.setForeground(QColor(RED))
        # 修正：使用 setFontItalic()
        commentFormat.setFontItalic(True)

        # 匹配器格式（紫色）
        matcherFormat = QTextCharFormat()
        matcherFormat.setForeground(QColor(PURPLE))
        matcherFormat.setFontWeight(QFont.Bold)

        # Nuclei POC 关键字
        keywords = [
            # 基本信息
            'id', 'info', 'name', 'author', 'severity', 'tags',
            'description', 'reference', 'classification',

            # 请求相关
            'requests', 'method', 'path', 'headers', 'body',
            'max-request', 'timeout', 'attack-type',

            # HTTP 方法
            'GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS', 'PATCH',

            # 匹配器类型
            'matchers', 'type', 'condition', 'part',

            # 匹配器子类型
            'status', 'regex', 'word', 'binary', 'size', 'dsl',

            # 提取器
            'extractors', 'kind', 'regex', 'json', 'xpath'
        ]

        # 特殊关键字
        specialKeywords = [
            'true', 'false', 'null',
            'critical', 'high', 'medium', 'low', 'info'
        ]

        # 匹配器关键字
        matcherKeywords = [
            'and', 'or', 'not',
            'contains', 'equals', 'matches'
        ]

        # 添加普通关键字高亮规则
        for keyword in keywords:
            pattern = QRegExp(f"\\b{keyword}\\b(?=\\s*:)")
            self.highlightingRules.append((pattern, keyFormat))

        # 添加特殊关键字高亮规则
        for keyword in specialKeywords:
            pattern = QRegExp(f"\\b{keyword}\\b")
            self.highlightingRules.append((pattern, specialKeyFormat))

        # 添加匹配器关键字高亮规则
        for keyword in matcherKeywords:
            pattern = QRegExp(f"\\b{keyword}\\b")
            self.highlightingRules.append((pattern, matcherFormat))

        # 值高亮（从冒号开始到行尾）
        valuePattern = QRegExp(":\\s*.*$")
        self.highlightingRules.append((valuePattern, valueFormat))

        # 注释高亮
        commentPattern = QRegExp("#.*$")
        self.highlightingRules.append((commentPattern, commentFormat))

        # URL 高亮
        urlFormat = QTextCharFormat()
        urlFormat.setForeground(QColor("#4169E1"))
        urlFormat.setFontUnderline(True)
        urlPattern = QRegExp("https?://\\S+")
        self.highlightingRules.append((urlPattern, urlFormat))

    def highlightBlock(self, text):
        for pattern, format in self.highlightingRules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)
        self.setCurrentBlockState(0)


class YamlTextEdit(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 使用 setCursorWidth() 方法设置光标宽度
        self.setCursorWidth(5)

        self.setTabStopDistance(QFontMetrics(self.font()).horizontalAdvance(' ') * 4)

        # 创建行号区域
        self.line_number_area = LineNumberArea(self)

        # 连接信号和槽
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        # 初始化行号区域
        self.update_line_number_area_width(0)
        self.highlight_current_line()

    def line_number_area_width(self):
        """计算行号区域宽度"""
        digits = max(1, len(str(self.blockCount())))
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        """更新行号区域宽度"""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        """更新行号区域"""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        """调整大小事件"""
        super().resizeEvent(event)

        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(
            cr.left(),
            cr.top(),
            self.line_number_area_width(),
            cr.height()
        ))

    def line_number_area_paint_event(self, event):
        """绘制行号区域"""
        painter = QPainter(self.line_number_area)

        # 使用与编辑器相同的背景色
        background_color = QColor(39, 40, 34)  # Monokai 主题的背景色
        painter.fillRect(event.rect(), background_color)

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        height = self.blockBoundingRect(block).height()

        while block.isValid():
            if not block.isVisible():
                block = block.next()
                block_number += 1
                continue

            # 绘制行号
            number = str(block_number + 1)

            # 设置字体颜色为红色
            painter.setPen(QColor(255, 0, 0))  # 鲜艳的红色

            painter.drawText(
                QRect(
                    0,
                    int(top),
                    self.line_number_area.width() - 3,
                    int(height)
                ),
                Qt.AlignRight | Qt.AlignVCenter,
                number
            )

            block = block.next()
            top += height
            block_number += 1
            height = self.blockBoundingRect(block).height()

    def highlight_current_line(self):
        """高亮当前行"""
        extra_selections = []

        if not self.isReadOnly():
            # 当前行高亮
            selection = QTextEdit.ExtraSelection()
            line_color = QColor(100, 100, 150, 50)  # 深蓝色，低透明度

            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()

            extra_selections.append(selection)

            # 光标所在位置特殊高亮
            cursor_selection = QTextEdit.ExtraSelection()
            cursor_color = QColor(255, 255, 0, 30)  # 黄色，极低透明度

            cursor_selection.format.setBackground(cursor_color)
            cursor_selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            cursor_selection.cursor = self.textCursor()
            cursor_selection.cursor.movePosition(QTextCursor.StartOfLine)
            cursor_selection.cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)

            extra_selections.append(cursor_selection)

        self.setExtraSelections(extra_selections)

    def keyPressEvent(self, event):
        """处理按键事件"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            cursor = self.textCursor()
            cursor.insertText('\n' + ' ' * self.get_indent_level(cursor.block().text()))
            return
        super().keyPressEvent(event)

    def get_indent_level(self, text):
        """获取缩进级别"""
        return len(text) - len(text.lstrip())

    def paintEvent(self, event):
        super().paintEvent(event)

        # 高亮光标
        painter = QPainter(self.viewport())
        cursor = self.textCursor()
        cursor_rect = self.cursorRect(cursor)

        # 高亮光标为白色，较高透明度
        highlight_color = QColor(255, 255, 255, 100)  # 白色，较高透明度
        painter.fillRect(cursor_rect, highlight_color)

        # 绘制垂直缩进线的代码保持不变
        font_metrics = self.fontMetrics()
        space_width = font_metrics.horizontalAdvance(' ')
        line_height = font_metrics.height()

        block = self.firstVisibleBlock()
        while block.isValid():
            text = block.text()
            if text.strip():
                # 计算缩进
                indent = len(text) - len(text.lstrip())
                if indent > 0:
                    x = indent * space_width
                    top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()

                    # 绘制垂直缩进线
                    painter.setPen(QColor(200, 200, 200, 100))  # 半透明灰色
                    painter.drawLine(
                        int(x), int(top),
                        int(x), int(top + line_height)
                    )

            block = block.next()


class FolderHistoryDialog(QDialog):
    def __init__(self, history, parent=None):
        super().__init__(parent)
        self.setWindowTitle("历史目录")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        # 保存父窗口引用
        self.main_window = parent

        # 添加一个标志，表示是否选择了文件夹
        self.folder_selected = False

        layout = QVBoxLayout(self)

        info_label = QLabel("选择历史目录或浏览新目录:")
        layout.addWidget(info_label)

        self.list_widget = QListWidget()
        self.list_widget.addItems(history)
        self.list_widget.itemDoubleClicked.connect(self.onItemDoubleClicked)
        # 启用多选
        self.list_widget.setSelectionMode(QAbstractItemView.MultiSelection)
        layout.addWidget(self.list_widget)

        button_layout = QHBoxLayout()

        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browseFolder)

        select_btn = QPushButton("选择")
        select_btn.clicked.connect(self.onSelectClicked)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)

        remove_btn = QPushButton("删除选中")
        remove_btn.clicked.connect(self.removeSelectedItems)

        clear_history_btn = QPushButton("清空历史")
        clear_history_btn.clicked.connect(self.clearHistory)

        button_layout.addWidget(browse_btn)
        button_layout.addWidget(select_btn)
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(remove_btn)
        button_layout.addWidget(clear_history_btn)
        layout.addLayout(button_layout)

        self.selected_folder = None

    def onItemDoubleClicked(self, item):
        """双击列表项时的处理"""
        self.selected_folder = item.text()
        self.folder_selected = True
        self.accept()

    def onSelectClicked(self):
        """点击选择按钮时的处理"""
        current_item = self.list_widget.currentItem()
        if current_item:
            self.selected_folder = current_item.text()
            self.folder_selected = True
            self.accept()
        else:
            QMessageBox.warning(self, "提示", "请选择一个目录")

    def browseFolder(self):
        """浏览新目录"""
        folder = QFileDialog.getExistingDirectory(self, "选择POC目录")
        if folder:
            self.selected_folder = folder
            self.folder_selected = True
            self.accept()

    def reject(self):
        """重写 reject 方法，确保不会意外打开文件管理器"""
        self.selected_folder = None
        self.folder_selected = False
        super().reject()

    def selectedFolder(self):
        """获取选择的文件夹"""
        return self.selected_folder if self.folder_selected else None

    def removeSelectedItems(self):
        # 获取选中的项目
        selected_items = [item.text() for item in self.list_widget.selectedItems()]

        if not selected_items:
            QMessageBox.warning(self, "提示", "请选择要删除的历史记录")
            return

        # 弹出确认对话框
        reply = QMessageBox.question(
            self,
            "删除历史",
            f"确定要删除中的 {len(selected_items)} 条历史记录吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 调用主窗口的删除方法
            if self.main_window and hasattr(self.main_window, 'removeSelectedFolderHistory'):
                self.main_window.removeSelectedFolderHistory(selected_items)

            # 从列表中移除选中项
            for item in selected_items:
                items = self.list_widget.findItems(item, Qt.MatchExactly)
                for item_widget in items:
                    self.list_widget.takeItem(self.list_widget.row(item_widget))

    def clearHistory(self):
        # 弹出确认对话框
        reply = QMessageBox.question(
            self,
            "清空历史",
            "确定要清空所有历史目录吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 调用主窗口的清空方法
            if self.main_window and hasattr(self.main_window, 'clearFolderHistory'):
                self.main_window.clearFolderHistory()

            # 清空列表
            self.list_widget.clear()

    def browseFolder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择POC目录")
        if folder:
            self.selected_folder = folder
            self.accept()

    def selectedFolder(self):
        if self.selected_folder:
            return self.selected_folder
        if self.list_widget.currentItem():
            return self.list_widget.currentItem().text()
        return None


class EditorWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        self.is_maximized = False
        self.original_geometry = None
        self.original_parent = None
        self.main_window = None
        self.setupContextMenu()
        self.current_theme = 0  # Track current theme
        self.themes = [
            {
                "name": "Monokai",
                "editor": """
                    QPlainTextEdit {
                        background-color: #272822;
                        color: #F8F8F2;
                        font-family: 'Courier New';
                        font-size: 8pt;
                        border: none;
                        border-bottom-left-radius: 5px;
                        border-bottom-right-radius: 5px;
                    }
                """,
                "key_color": "#1E90FF",
                "value_color": "#32CD32",
                "comment_color": "#B22222",
                "title_bar": "background-color: #2D2D2D;"
            },
            {
                "name": "Light",
                "editor": """
                    QPlainTextEdit {
                        background-color: #FFFFFF;
                        color: #2D2D2D;
                        font-family: 'Consolas';
                        font-size: 11pt;
                        border: none;
                        border-bottom-left-radius: 5px;
                        border-bottom-right-radius: 5px;
                    }
                """,
                "key_color": "#0033CC",
                "value_color": "#008000",
                "comment_color": "#808080",
                "title_bar": "background-color: #F0F0F0;"
            },
            {
                "name": "Dark",
                "editor": """
                    QPlainTextEdit {
                        background-color: #1E1E1E;
                        color: #D4D4D4;
                        font-family: 'Source Code Pro';
                        font-size: 13pt;
                        border: none;
                        border-bottom-left-radius: 5px;
                        border-bottom-right-radius: 5px;
                    }
                """,
                "key_color": "#569CD6",
                "value_color": "#4EC9B0",
                "comment_color": "#608B4E",
                "title_bar": "background-color: #333333;"
            }
        ]

    def initUI(self):

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Title bar
        title_bar = QFrame()
        title_bar.setStyleSheet("""
            QFrame {
                background-color: #2D2D2D;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
        """)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 5, 10, 5)
        title_label = QLabel("POC编辑器")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        # Maximize button
        self.maximize_btn = QPushButton("□")  # 最大化按钮
        self.maximize_btn.setFixedSize(22, 27)
        self.maximize_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 20px;
            }
            QPushButton:hover {
                background-color: #404040;
                border-radius: 3px;
            }
        """)
        self.maximize_btn.clicked.connect(self.toggleMaximize)
        title_layout.addWidget(self.maximize_btn)

        layout.addWidget(title_bar)

        # Editor
        self.editor = YamlTextEdit()
        self.editor.setStyleSheet("""
            QPlainTextEdit {
                background-color: #272822;
                color: #F8F8F2;
                font-family: 'Courier New';
                font-size: 10pt;
                border: none;
                border-bottom-left-radius: 5px;
                border-bottom-right-radius: 5px;
            }
        """)
        self.highlighter = NucleiPOCHighlighter(self.editor.document())
        layout.addWidget(self.editor)

    def setupContextMenu(self):
        self.editor.setContextMenuPolicy(Qt.CustomContextMenu)
        self.editor.customContextMenuRequested.connect(self.showContextMenu)

    def showContextMenu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2D2D2D;
                color: white;
                border: 1px solid #404040;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #404040;
            }
        """)

        copy_action = menu.addAction("复制")
        paste_action = menu.addAction("粘贴")
        cut_action = menu.addAction("剪切")

        action = menu.exec_(self.editor.mapToGlobal(pos))

        if action == copy_action:
            self.editor.copy()
        elif action == paste_action:
            self.editor.paste()
        elif action == cut_action:
            self.editor.cut()

    def toggleMaximize(self):
        if not self.is_maximized:
            parent = self.parent()
            while parent and not isinstance(parent, QMainWindow):
                parent = parent.parent()

            if parent:
                self.main_window = parent
                self.original_geometry = self.geometry()
                self.original_parent = self.parent()

                central_widget = self.main_window.centralWidget()
                main_rect = central_widget.rect()
                global_pos = central_widget.mapToGlobal(main_rect.topLeft())

                self.setParent(None)
                self.setGeometry(QRect(global_pos, main_rect.size()))
                self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
                self.show()
                self.maximize_btn.setText("❐")
                self.raise_()
                self.activateWindow()
        else:
            if self.original_parent and self.original_geometry:
                self.setParent(self.original_parent)
                self.setGeometry(self.original_geometry)
                self.setWindowFlags(Qt.Widget)
                self.show()
                self.maximize_btn.setText("□")

        self.is_maximized = not self.is_maximized

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.is_maximized:
            self.toggleMaximize()
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if self.is_maximized:
            self.drag_pos = event.globalPos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_maximized and hasattr(self, 'drag_pos'):
            delta = event.globalPos() - self.drag_pos
            self.move(self.pos() + delta)
            self.drag_pos = event.globalPos()
        super().mouseMoveEvent(event)


# 新增一个线程类用于加载POC
class LoadPOCThread(QThread):
    finished = pyqtSignal(list)  # 定义信号，用于传递加载的POC数据
    progress = pyqtSignal(int)  # 定义信号，用于更新进度

    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path

    def run(self):
        yaml_data = []
        total_files = 0

        # 计算文件总数
        for root, _, files in os.walk(self.folder_path):
            total_files += sum(1 for file in files if file.lower().endswith('.yaml'))

        processed_files = 0  # 处理的文件计数

        try:
            for root, _, files in os.walk(self.folder_path):
                for file in files:
                    if file.lower().endswith('.yaml'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                data = yaml.safe_load(content)
                                if isinstance(data, dict):
                                    # 获取相对路径
                                    relative_path = os.path.relpath(file_path, self.folder_path)
                                    data['original_filename'] = relative_path  # 使用相对路径加文件名
                                    data['file_path'] = file_path
                                    yaml_data.append(data)
                        except Exception as e:
                            print(f"加载文件出错 {file}: {str(e)}")

                        processed_files += 1
                        self.progress.emit(int((processed_files / total_files) * 100))  # 更新进度

        except Exception as e:
            print(f"加载目录失败: {str(e)}")

        self.finished.emit(yaml_data)  # 发射信号，传递加载的数据


class NucleiPOCManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.temp_dirs = []  # 用于存储临时目录路径
        self.yaml_data = []
        self.filtered_yaml_data = []
        self.yaml_folder_path = None
        self.temp_dirs = []
        self.current_page = 1
        self.rows_per_page = 50
        self.search_keyword = ''
        self.folder_history = self.loadFolderHistory()
        self.initUI()
        self.load_thread = None  # 初始化线程变量
        self.loadLastFolder()

    def initUI(self):
        self.setWindowTitle("Nuclei POC 管理工具by-hugh")
        self.setGeometry(100, 100, 1280, 840)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F0F0F0;
            }
            QPushButton {
                background-color: #4A90E2;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
            QLineEdit {
                padding: 5px;
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                background-color: white;
            }
            QTableWidget {
                background-color: white;
                gridline-color: #E5E5E5;
            }
            QHeaderView::section {
                background-color: #4A90E2;
                color: white;
                padding: 5px;
                border: none;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create main vertical layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # Top search bar
        top_layout = QHBoxLayout()
        self.search_line_edit = QLineEdit()
        self.search_line_edit.setPlaceholderText("全局搜索 (支持 AND/OR 操作)")
        self.search_line_edit.setClearButtonEnabled(True)
        self.search_line_edit.textChanged.connect(self.onSearchTextChanged)

        self.search_button = QPushButton("搜索")
        self.search_button.clicked.connect(lambda: self.searchTable(self.search_line_edit.text()))

        reset_button = QPushButton("重置")
        reset_button.clicked.connect(self.resetSearch)

        folder_button = QPushButton("打开目录")
        folder_button.clicked.connect(self.selectFolder)

        self.total_files_label = QLabel("POC总数: 0")

        top_layout.addWidget(self.search_line_edit)
        top_layout.addWidget(self.search_button)
        top_layout.addWidget(reset_button)
        top_layout.addWidget(folder_button)
        top_layout.addWidget(self.total_files_label)

        # Create main vertical splitter
        main_splitter = QSplitter(Qt.Vertical)

        # Top container for table and pagination
        top_container = QWidget()
        top_layout_container = QVBoxLayout(top_container)
        top_layout_container.setContentsMargins(0, 0, 0, 0)

        # Add search bar
        top_layout_container.addLayout(top_layout)

        # Add table
        self.tableWidget = QTableWidget()
        self.setupTable()
        top_layout_container.addWidget(self.tableWidget)

        # Add pagination
        pagination_layout = QHBoxLayout()
        pagination_layout.addStretch()  # 添加弹性空间将按钮移到右侧

        # 缩小按钮宽度
        self.prev_page_btn = QPushButton("上一页")
        self.prev_page_btn.setFixedWidth(60)  # 设置按钮宽度

        self.next_page_btn = QPushButton("下一页")
        self.next_page_btn.setFixedWidth(60)  # 设置按钮宽度

        self.page_label = QLabel()

        self.page_input = QLineEdit()
        self.page_input.setFixedWidth(50)  # 设置输入框宽度
        self.page_input.setPlaceholderText("页码")

        self.goto_page_btn = QPushButton("跳转")
        self.goto_page_btn.setFixedWidth(60)  # 设置按钮宽度

        self.prev_page_btn.clicked.connect(self.prevPage)
        self.next_page_btn.clicked.connect(self.nextPage)
        self.goto_page_btn.clicked.connect(self.gotoPage)

        pagination_layout.addWidget(self.prev_page_btn)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.page_input)
        pagination_layout.addWidget(self.goto_page_btn)
        pagination_layout.addWidget(self.next_page_btn)

        top_layout_container.addLayout(pagination_layout)

        # Add top container to main splitter
        main_splitter.addWidget(top_container)

        # Bottom container with horizontal splitter
        bottom_splitter = QSplitter(Qt.Horizontal)

        # Target input area
        target_container = QWidget()
        target_layout = QVBoxLayout(target_container)
        target_layout.setContentsMargins(5, 5, 5, 5)

        target_label = QLabel("扫描目标 (每行一个)")
        self.target_input = QPlainTextEdit()
        self.target_input.setPlaceholderText("输入扫描目标，每行一个")

        target_layout.addWidget(target_label)
        target_layout.addWidget(self.target_input)
        bottom_splitter.addWidget(target_container)

        # Editor widget
        self.editor_widget = EditorWidget()
        bottom_splitter.addWidget(self.editor_widget)

        # Set the initial sizes for horizontal splitter (30% - 70%)
        bottom_splitter.setSizes([int(self.width() * 0.3), int(self.width() * 0.7)])

        # Add bottom splitter to main splitter
        main_splitter.addWidget(bottom_splitter)

        # Set the initial sizes for vertical splitter (60% - 40%)
        main_splitter.setSizes([int(self.height() * 0.6), int(self.height() * 0.4)])

        # Add main splitter to layout
        main_layout.addWidget(main_splitter)

        # Bottom control bar
        bottom_layout = QHBoxLayout()

        proxy_label = QLabel("代理设置:")
        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText("http://127.0.0.1:8080")

        self.dresp_checkbox = QCheckBox("显示详细结果")

        self.run_button = QPushButton("运行")
        self.run_button.clicked.connect(self.runNuclei)

        self.batch_button = QPushButton("批量运行")
        self.batch_button.clicked.connect(self.runNucleiBatch)

        self.debug_button = QPushButton("调试")
        self.debug_button.setStyleSheet("""
            QPushButton {
                background-color: #FF4500;  /* 橙红色背景 */
                color: white;  /* 白色文字 */
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #FF6347;  /* 略浅的橙红色 */
            }
        """)
        self.debug_button.clicked.connect(self.debugNuclei)

        save_button = QPushButton("保存")
        save_button.clicked.connect(self.saveYamlContent)

        exit_button = QPushButton("退出")
        exit_button.clicked.connect(self.close)

        bottom_layout.addWidget(proxy_label)
        bottom_layout.addWidget(self.proxy_input)
        bottom_layout.addWidget(self.dresp_checkbox)
        bottom_layout.addWidget(self.debug_button)
        bottom_layout.addWidget(self.run_button)
        bottom_layout.addWidget(self.batch_button)
        bottom_layout.addWidget(save_button)
        bottom_layout.addWidget(exit_button)

        main_layout.addLayout(bottom_layout)

    def setupTable(self):
        self.tableWidget.setColumnCount(8)
        headers = ['序号', '文件名', '危害', '作者', '标签', 'CVE编号', '参考链接', '漏洞描述']
        self.tableWidget.setHorizontalHeaderLabels(headers)

        # 禁用排序功能
        self.tableWidget.setSortingEnabled(False)

        # 设置交替行颜色
        self.tableWidget.setAlternatingRowColors(True)
        self.tableWidget.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;  /* 白色背景 */
                gridline-color: #E5E5E5;  /* 网格线颜色 */
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #4A90E2;  /* 选中行的背景色 */
                color: white;  /* 选中行的文字颜色 */
            }
            QTableWidget::item:hover {
                background-color: #D0E1F9;  /* 鼠标悬停行的背景色 */
            }
        """)

        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.setShowGrid(True)

        widths = [40, 255, 60, 100, 160, 106, 310, 0]
        for col, width in enumerate(widths):
            if width > 0:
                self.tableWidget.setColumnWidth(col, width)

        self.tableWidget.horizontalHeader().setStretchLastSection(True)
        self.tableWidget.cellClicked.connect(self.onTableCellClicked)
        self.tableWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableWidget.customContextMenuRequested.connect(self.showContextMenu)

    def validateRunPrerequisites(self):
        targets = self.target_input.toPlainText().strip()
        if not targets:
            QMessageBox.warning(self, "错误", "请输入扫描目标")
            return False

        if not self.yaml_folder_path:
            QMessageBox.warning(self, "错误", "请先选择POC目录")
            return False

        return True

    def loadFolderHistory(self):
        history_file = os.path.join(os.path.expanduser('~'), '.nuclei_manager_history')
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except:
            return []

    def saveFolderHistoryList(self, history_list):
        """
        保存历史��录列表
        :param history_list: 保存的历史记录列表
        """
        history_file = os.path.join(os.path.expanduser('~'), '.nuclei_manager_history')
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                for folder in history_list:
                    f.write(f"{folder}\n")
        except Exception as e:
            print(f"保存历史记录失败: {e}")

    def saveFolderHistory(self, folder_path):
        if not folder_path:
            return

        history = self.loadFolderHistory()
        # 如果已存在，先移除
        if folder_path in history:
            history.remove(folder_path)
        # 插入到列表开头
        history.insert(0, folder_path)
        # 保留最近的10条记录
        history = history[:10]

        history_file = os.path.join(os.path.expanduser('~'), '.nuclei_manager_history')
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                for folder in history:
                    f.write(f"{folder}\n")

            # 立即更新内存中的历史记录
            self.folder_history = history
        except Exception as e:
            print(f"保存历史记录失败: {e}")

    def removeSelectedFolderHistory(self, selected_items):
        """
        删除选中���历史记录
        :param selected_items: 选中的历史记录列表
        """
        if not selected_items:
            return

        # 直接从配置中读取最新的历史记录
        history = self.loadFolderHistory()

        # 删除选中的历史记录
        history = [folder for folder in history if folder not in selected_items]

        # 立即保存更新后的历史记录
        history_file = os.path.join(os.path.expanduser('~'), '.nuclei_manager_history')
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                for folder in history:
                    f.write(f"{folder}\n")

            # 立即更新内存中的历史记录
            self.folder_history = history

            # 如果有历史记录对话框，更新其列表
            if hasattr(self, 'folder_history_dialog'):
                self.folder_history_dialog.list_widget.clear()
                self.folder_history_dialog.list_widget.addItems(history)
        except Exception as e:
            print(f"删除历史记录失败: {e}")

    def clearFolderHistory(self):
        """
        清空所有历史记录
        """
        history_file = os.path.join(os.path.expanduser('~'), '.nuclei_manager_history')
        try:
            # 直接删除文件或清空文件内��
            open(history_file, 'w').close()

            # 立即更新内存中的历史记录
            self.folder_history = []

            # 如果有历史记录对话框，清空其列表
            if hasattr(self, 'folder_history_dialog'):
                self.folder_history_dialog.list_widget.clear()
        except Exception as e:
            print(f"清空历史记录失败: {e}")

    def updateFolderHistoryUI(self, history_list):
        """
        更新UI中的历史记录显示
        :param history_list: 新的历史记录列表
        """
        # 如果有历史记录对话框，更新其列表
        if hasattr(self, 'folder_history_dialog'):
            self.folder_history_dialog.list_widget.clear()
            self.folder_history_dialog.list_widget.addItems(history_list)

    def loadLastFolder(self):
        if self.folder_history:
            last_folder = self.folder_history[0]
            if os.path.exists(last_folder):
                self.loadFolder(last_folder)

    def selectFolder(self):
        # 如果没有历史记录，直接打开文件管理器
        if not self.folder_history:
            folder = QFileDialog.getExistingDirectory(self, "选择POC目录")
            if folder:
                self.loadFolder(folder)
                self.saveFolderHistory(folder)
            return

        # 如果历史记录，使用历史记录对话框
        dialog = FolderHistoryDialog(self.folder_history, self)
        dialog_result = dialog.exec_()

        # 如果取消或关闭对话框，使用最近一次的历史目录
        if dialog_result != QDialog.Accepted:
            if self.folder_history and os.path.exists(self.folder_history[0]):
                self.loadFolder(self.folder_history[0])
            return

        # 处理明确选择的情况
        selected = dialog.selectedFolder()
        if selected and os.path.exists(selected):
            self.loadFolder(selected)
            self.saveFolderHistory(selected)

    def loadFolder(self, folder_path):
        self.yaml_folder_path = folder_path
        self.yaml_data = []  # 清空旧数据
        self.filtered_yaml_data = []  # 清空过滤数据

        # 创建并启动加载POC的线程
        self.load_thread = LoadPOCThread(folder_path)
        self.load_thread.finished.connect(self.onLoadFinished)  # 连接信号
        self.load_thread.progress.connect(self.updateProgress)  # 连接进度信号

        # 创建进度对话框
        self.progress_dialog = QProgressDialog("正在加载POC文件，请稍候...", "取消", 0, 100, self)
        self.progress_dialog.setWindowTitle("加载中")
        self.progress_dialog.setModal(True)
        self.progress_dialog.setMinimumDuration(0)  # 立即显示对话框
        self.progress_dialog.setStyleSheet("""
            QProgressDialog {
                background-color: #F0F0F0;
                border: 2px solid #4A90E2;
                border-radius: 10px;
            }
            QProgressBar {
                background-color: #FFFFFF;
                border: 1px solid #4A90E2;
                border-radius: 5px;
            }
            QProgressBar::chunk {
                background-color: #4A90E2;
                border-radius: 5px;
            }
            QPushButton {
                background-color: #4A90E2;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
        """)
        self.progress_dialog.setValue(0)  # 初始化进度为0

        self.load_thread.start()  # 启动线程

    def updateProgress(self, value):
        self.progress_dialog.setValue(value)  # 更新进度条的值
        if value >= 100:
            self.progress_dialog.setLabelText("加载完成！")  # 加载完成时更新文本

    def onLoadFinished(self, yaml_data):
        self.progress_dialog.close()  # 关闭进度对话框
        self.yaml_data = yaml_data  # 更新POC数据
        self.updateTable()  # 确保更新表格
        self.updatePageInfo()  # 更新分页信息
        self.total_files_label.setText(f"POC总数: {len(self.yaml_data)}")

    def updateTable(self):
        self.tableWidget.setRowCount(0)  # 清空表格行
        data = self.filtered_yaml_data if self.filtered_yaml_data else self.yaml_data

        # 计算当前页的起始和结束索引
        start = (self.current_page - 1) * self.rows_per_page
        end = min(start + self.rows_per_page, len(data))

        # 设置表格行数
        self.tableWidget.setRowCount(end - start)

        severity_map = {
            'critical': '严重',
            'high': '高危',
            'medium': '中危',
            'low': '低危',
            'info': '信息'
        }

        color_map = {
            'critical': QColor("#FF0000"),  # 红色
            'high': QColor("#FFA500"),  # 橙色
            'medium': QColor("#FFD700"),  # 金色
            'low': QColor("#008000"),  # 绿色
            'info': QColor("#0000FF")  # 色
        }

        for row, item in enumerate(data[start:end]):
            info = item.get('info', {})

            self.tableWidget.setItem(row, 0, QTableWidgetItem(str(start + row + 1)))
            self.tableWidget.setItem(row, 1, QTableWidgetItem(item.get('original_filename', '')))  # 这里将显示相对路径

            severity = severity_map.get(info.get('severity', '').lower(), info.get('severity', ''))
            severity_item = QTableWidgetItem(severity)
            severity_item.setForeground(color_map.get(info.get('severity', '').lower(), QColor("#000000")))  # 设置字体颜色
            self.tableWidget.setItem(row, 2, severity_item)

            self.tableWidget.setItem(row, 3, QTableWidgetItem(info.get('author', '')))

            tags = info.get('tags', [])
            if isinstance(tags, list):
                tags = ', '.join(tags)
            self.tableWidget.setItem(row, 4, QTableWidgetItem(str(tags)))

            cve = info.get('classification', {}).get('cve-id', '')
            self.tableWidget.setItem(row, 5, QTableWidgetItem(str(cve)))

            reference = info.get('reference', [])
            if isinstance(reference, list) and reference:
                reference = reference[0]
            self.tableWidget.setItem(row, 6, QTableWidgetItem(str(reference)))

            self.tableWidget.setItem(row, 7, QTableWidgetItem(info.get('description', '')))

        # 更新分页信息
        self.updatePageInfo()

    def updatePageInfo(self):
        data = self.filtered_yaml_data if self.filtered_yaml_data else self.yaml_data
        total_pages = max(1, (len(data) + self.rows_per_page - 1) // self.rows_per_page)
        self.page_label.setText(f"第 {self.current_page} / {total_pages} 页")

        self.prev_page_btn.setEnabled(self.current_page > 1)
        self.next_page_btn.setEnabled(self.current_page < total_pages)

    def prevPage(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.updateTable()
            self.updatePageInfo()

    def nextPage(self):
        data = self.filtered_yaml_data if self.filtered_yaml_data else self.yaml_data
        total_pages = (len(data) + self.rows_per_page - 1) // self.rows_per_page

        if self.current_page < total_pages:
            self.current_page += 1
            self.updateTable()
            self.updatePageInfo()

    def gotoPage(self):
        try:
            page = int(self.page_input.text())
            data = self.filtered_yaml_data if self.filtered_yaml_data else self.yaml_data
            total_pages = (len(data) + self.rows_per_page - 1) // self.rows_per_page

            if 1 <= page <= total_pages:
                self.current_page = page
                self.updateTable()
                self.updatePageInfo()
            else:
                QMessageBox.warning(self, "警告", f"页码必须在 1 到 {total_pages} 之间")
        except ValueError:
            QMessageBox.warning(self, "警告", "请输入有效的页码")

    def onTableCellClicked(self, row):
        try:
            self.highlightRow(row)  # 添加此行以高亮选中行
            data = self.filtered_yaml_data if self.filtered_yaml_data else self.yaml_data
            start = (self.current_page - 1) * self.rows_per_page
            item = data[start + row]
            file_path = item.get('file_path')

            if file_path and os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.editor_widget.editor.setPlainText(content)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法加载POC内容: {str(e)}")

    def highlightRow(self, row):
        """高亮选中行"""
        # 清除之前高亮的行
        for r in range(self.tableWidget.rowCount()):
            for column in range(self.tableWidget.columnCount()):
                item = self.tableWidget.item(r, column)
                if item:
                    # 恢复为交���行颜色或白色背景
                    if r % 2 == 0:
                        item.setBackground(QColor(255, 255, 255))  # 偶数行恢复为白色
                    else:
                        item.setBackground(QColor(240, 240, 240))  # 奇数行恢复为浅灰色

        # 高亮当前行
        for column in range(self.tableWidget.columnCount()):
            item = self.tableWidget.item(row, column)
            if item:
                item.setBackground(QColor(220, 220, 255))  # 设置为浅蓝色

    def showContextMenu(self, position):
        menu = QMenu()
        copy_name = menu.addAction("复制文件名")
        copy_path = menu.addAction("复制文件路径")
        open_location = menu.addAction("打开文件位置")
        menu.addSeparator()
        delete_action = menu.addAction("删除文件")

        action = menu.exec_(self.tableWidget.mapToGlobal(position))
        if not action:
            return

        item = self.tableWidget.itemAt(position)
        if not item:
            return

        row = item.row()
        start = (self.current_page - 1) * self.rows_per_page
        data = self.filtered_yaml_data if self.filtered_yaml_data else self.yaml_data
        file_data = data[start + row]
        file_path = file_data.get('file_path')
        file_name = file_data.get('original_filename')

        if action == copy_name:
            QApplication.clipboard().setText(file_name)
            QMessageBox.information(self, "提示", "文件名已复制到剪贴板")
        elif action == copy_path:
            QApplication.clipboard().setText(file_path)
            QMessageBox.information(self, "提示", "文件路径已复制到剪贴板")
        elif action == open_location:
            try:
                file_path = os.path.abspath(file_path)  # Convert to absolute path
                if sys.platform == 'win32':
                    subprocess.run(['explorer', '/select,', file_path])
                elif sys.platform == 'darwin':
                    subprocess.run(['open', '-R', file_path])
                else:
                    folder_path = os.path.dirname(file_path)
                    subprocess.run(['xdg-open', folder_path])
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法打开文件位置: {str(e)}")
        elif action == delete_action:
            self.deleteFile(row, file_name, file_path)

    def deleteFile(self, row, file_name, file_path):
        reply = QMessageBox.question(self, '确认删除',
                                     f"确定要删除文件 {file_name} 吗？",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                os.remove(file_path)
                start = (self.current_page - 1) * self.rows_per_page
                if self.filtered_yaml_data:
                    self.filtered_yaml_data.pop(start + row)
                self.yaml_data = [x for x in self.yaml_data if x.get('file_path') != file_path]
                self.updateTable()
                self.updatePageInfo()
                self.total_files_label.setText(f"POC总数: {len(self.yaml_data)}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除文件失败: {str(e)}")

    def searchTable(self, keyword):
        self.search_keyword = keyword
        self.filtered_yaml_data = []

        if not keyword:
            self.filtered_yaml_data = self.yaml_data
        else:
            keywords = keyword.split()
            use_and = 'AND' in keywords
            if use_and:
                keywords.remove('AND')
            elif 'OR' in keywords:
                keywords.remove('OR')
                use_and = False

            for item in self.yaml_data:
                yaml_str = yaml.dump(item, allow_unicode=True).lower()
                if use_and:
                    if all(kw.lower() in yaml_str for kw in keywords):
                        self.filtered_yaml_data.append(item)
                else:
                    if any(kw.lower() in yaml_str for kw in keywords):
                        self.filtered_yaml_data.append(item)

        self.current_page = 1
        self.updateTable()
        self.updatePageInfo()

        result_count = len(self.filtered_yaml_data)
        if keyword:
            QMessageBox.information(self, "搜索结果", f"找到 {result_count} 个匹配项")

    def onSearchTextChanged(self, text):
        if not text:
            self.searchTable('')

    def resetSearch(self):
        self.search_line_edit.clear()
        self.filtered_yaml_data = []
        self.current_page = 1
        self.updateTable()
        self.updatePageInfo()

    def saveYamlContent(self):
        content = self.editor_widget.editor.toPlainText()
        if not content.strip():
            QMessageBox.warning(self, "警告", "编辑器内容为空")
            return

        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()

        selected_row = self.tableWidget.currentRow()
        is_new_file = selected_row < 0

        if is_new_file:
            file_name, ok = QInputDialog.getText(self, "保存文件",
                                                 "输入文件名:",
                                                 QLineEdit.Normal, "")
            if not ok or not file_name.strip():
                return

            if not file_name.endswith('.yaml'):
                file_name += '.yaml'
        else:
            start = (self.current_page - 1) * self.rows_per_page
            data = self.filtered_yaml_data if self.filtered_yaml_data else self.yaml_data
            file_name = data[start + selected_row].get('original_filename')

        try:
            file_path = os.path.join(self.yaml_folder_path, file_name)

            if is_new_file and os.path.exists(file_path):
                reply = QMessageBox.question(self, "文件已存在",
                                             f"文件 {file_name} 已存在，是否覆盖？",
                                             QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.No:
                    return

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            yaml_data = yaml.safe_load(content)
            yaml_data['original_filename'] = file_name
            yaml_data['file_path'] = file_path

            if is_new_file:
                self.yaml_data.append(yaml_data)
            else:
                start = (self.current_page - 1) * self.rows_per_page
                if self.filtered_yaml_data:
                    self.filtered_yaml_data[start + selected_row] = yaml_data
                for i, item in enumerate(self.yaml_data):
                    if item.get('file_path') == file_path:
                        self.yaml_data[i] = yaml_data
                        break

            self.updateTable()
            self.updatePageInfo()
            self.total_files_label.setText(f"POC总数: {len(self.yaml_data)}")
            QMessageBox.information(self, "成功", f"文件已保存: {file_name}")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存文件失败: {str(e)}")

    def runNuclei(self):
        try:
            # 验证运行前提条件
            if not self.validateRunPrerequisites():
                return

            # 获取输入的扫描目标
            targets = self.target_input.toPlainText().strip()
            if not targets:
                QMessageBox.warning(self, "输入错误", "请输入有效的扫描目标。")
                return

            # 将目标保存到临时文件
            temp_file_path = self.save_targets_file(targets)

            # 检查是否有行被选中
            selected_row = self.tableWidget.currentRow()
            if selected_row < 0:
                QMessageBox.warning(self, "���误", "请选择要运行的POC")
                return

            # 获取当前选中的文件路径
            file_name = self.tableWidget.item(selected_row, 1).text()  # 假定文件名在二列
            file_path = os.path.join(self.yaml_folder_path, file_name)

            # 检查模板文件是否存在
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "错误", f"模板文件不存在: {file_path}")
                return

            # 打印调试信息
            print("Executing command with template:", file_path)

            # 构建Nuclei命令
            cmd = ["nuclei", "-t", file_path, "-l", temp_file_path]
            if self.dresp_checkbox.isChecked():
                cmd.append("--dresp")
            if self.proxy_input.text():
                cmd.extend(["-proxy", self.proxy_input.text()])

            # 执行命令
            self.execute_command_in_terminal(cmd)
            print(cmd)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"运行Nuclei时发生错误: {str(e)}")

    def save_targets_file(self, targets):
        """将目标保存到临时文件并返回文件路径"""
        try:
            # 获取当前工作目录
            current_dir = os.path.dirname(os.path.abspath(__file__))  # 获取当前脚本所在的目录
            # 在当前目录中创建targets.txt文件的路径
            temp_file_path = os.path.join(current_dir, "targets.txt")
            # 目标写入文件
            with open(temp_file_path, 'w', encoding='utf-8') as file:
                file.write(targets)
            return temp_file_path
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存目标文件失败: {str(e)}")
            return None

    def execute_command_in_terminal(self, cmd):
        """在终端中执行命令"""
        try:
            if sys.platform == 'win32':
                subprocess.Popen(["start", "cmd", "/k"] + cmd, shell=True)
            elif sys.platform == 'darwin':
                script = f'tell application "Terminal" to do script "{" ".join(map(shlex.quote, cmd))}"'
                subprocess.Popen(['osascript', '-e', script])
            else:
                subprocess.Popen(['x-terminal-emulator', '-e',
                                  f'bash -c "{" ".join(map(shlex.quote, cmd))}; exec bash"'])
        except Exception as e:
            QMessageBox.critical(self, "错误", f"执行命令失败: {str(e)}")

    def runNucleiBatch(self):
        try:
            # 验证运行前提条件
            if not self.validateRunPrerequisites():
                return

            # 获取输入的扫描目标
            targets = self.target_input.toPlainText().strip()
            if not targets:
                QMessageBox.warning(self, "输入错误", "请输入有效的扫描目标。")
                return

            # 将目标保存到临时文件
            temp_file_path = self.save_targets_file(targets)

            # 从过滤后的数据中收集所有 YAML 文件名
            file_names = [item['original_filename'] for item in self.filtered_yaml_data]

            # 如果没有找到文件，显示警告
            if not file_names:
                QMessageBox.warning(self, "操作错误", "没有找到匹配的文件。")
                return

            # 生成唯一的临时目录名，并当前目录下创建
            unique_temp_dir_name = str(uuid.uuid4())
            current_dir = os.path.dirname(os.path.abspath(__file__))  # 获取当前脚本所在的目录
            temp_dir_path = os.path.join(current_dir, 'temp', unique_temp_dir_name)

            # 确保临时目录存在
            os.makedirs(temp_dir_path, exist_ok=True)

            # 将临时目录路径添加到列表中
            self.temp_dirs.append(temp_dir_path)

            # 复制文件到临时目录
            for file_name in file_names:
                source_path = os.path.join(self.yaml_folder_path, file_name)
                # 建目标文件的完整路径
                destination_path = os.path.join(temp_dir_path, file_name)

                # 确保目标文件的目录存在
                destination_dir = os.path.dirname(destination_path)
                os.makedirs(destination_dir, exist_ok=True)

                # 复制文件
                shutil.copy(source_path, destination_path)

            # 构建 Nuclei 命令
            cmd = ["nuclei", "-t", temp_dir_path, "-l", temp_file_path]
            if self.dresp_checkbox.isChecked():
                cmd.append("--dresp")
            if self.proxy_input.text():
                cmd.extend(["-proxy", self.proxy_input.text()])

            # 使用系统自带的命令行窗口执行命令
            self.execute_command_in_terminal(cmd)
            print(cmd)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"批量运行Nuclei时发生错误: {str(e)}")

    def closeEvent(self, event):
        """在关闭窗口时清理临时文件"""
        self.cleanup_temp_dirs()
        event.accept()  # 允许关闭事件

    def cleanup_temp_dirs(self):
        """清理所有临时目录"""
        for temp_dir in self.temp_dirs:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)  # 删除临时目录及其内容
        self.temp_dirs.clear()  # 清空临时目录列表

    def debugNuclei(self):
        """执行 Nuclei 调试模式"""
        try:
            # 验证运行前提条件
            if not self.validateRunPrerequisites():
                return

            # 获取输入的扫描目标
            targets = self.target_input.toPlainText().strip()
            if not targets:
                QMessageBox.warning(self, "输入错误", "请输入有效的扫描目标。")
                return

            # 将目标保存到临时文件
            temp_file_path = self.save_targets_file(targets)

            # 检查是否有行被选中
            selected_row = self.tableWidget.currentRow()
            if selected_row < 0:
                QMessageBox.warning(self, "错误", "请选择要调试的POC")
                return

            # 获取当前选中的文件路径
            file_name = self.tableWidget.item(selected_row, 1).text()
            file_path = os.path.join(self.yaml_folder_path, file_name)

            # 检查模板文件是否存在
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "错误", f"模板文件不存在: {file_path}")
                return

            # 构建 Nuclei 调试命令
            cmd = ["nuclei", "-t", file_path, "-l", temp_file_path, "-debug"]
            if self.dresp_checkbox.isChecked():
                cmd.append("--dresp")
            if self.proxy_input.text():
                cmd.extend(["-proxy", self.proxy_input.text()])

            # 执行命令
            self.execute_command_in_terminal(cmd)
            print(cmd)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"调试Nuclei时发生错误: {str(e)}")


def executeNucleiCommand(self, template_args):
    targets = self.target_input.toPlainText().strip()
    temp_targets = os.path.join(os.path.dirname(self.yaml_folder_path), "targets.txt")

    try:
        with open(temp_targets, 'w', encoding='utf-8') as f:
            f.write(targets)

        cmd = ["nuclei"] + template_args + ["-l", temp_targets]

        if self.dresp_checkbox.isChecked():
            cmd.append("--dresp")

        if self.proxy_input.text().strip():
            cmd.extend(["-proxy", self.proxy_input.text().strip()])

        if sys.platform == 'win32':
            subprocess.Popen(["start", "cmd", "/k"] + cmd, shell=True)
        elif sys.platform == 'darwin':
            script = f'tell application "Terminal" to do script "{" ".join(map(shlex.quote, cmd))}"'
            subprocess.Popen(['osascript', '-e', script])
        else:
            subprocess.Popen(['x-terminal-emulator', '-e',
                              f'bash -c "{" ".join(map(shlex.quote, cmd))}; exec bash"'])

    except Exception as e:
        QMessageBox.critical(self, "错误", f"执行命令失败: {str(e)}")
    finally:
        if os.path.exists(temp_targets):
            os.remove(temp_targets)


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    window = NucleiPOCManager()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
