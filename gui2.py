
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
                             QFrame, QScrollArea, QListWidgetItem, QDialogButtonBox)
from PyQt5.QtGui import (QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QPainter,
                         QFontMetrics, QPalette)
from PyQt5.QtCore import Qt, QRegExp, QSize, QRect, QPoint


class YamlHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlightingRules = []

        keyFormat = QTextCharFormat()
        keyFormat.setForeground(QColor("#1E90FF"))
        keyFormat.setFontWeight(QFont.Bold)

        valueFormat = QTextCharFormat()
        valueFormat.setForeground(QColor("#32CD32"))

        commentFormat = QTextCharFormat()
        commentFormat.setForeground(QColor("#B22222"))

        keywords = ['id', 'info', 'name', 'author', 'metadata', 'fofa-query',
                    '360-query', 'hunter-query', 'verified', 'severity', 'tags',
                    'description', 'requests', 'matchers', 'type', 'POST', 'GET',
                    'PUT', 'reference', 'max-request', 'http', 'regex', 'dsl',
                    'extractors']

        for keyword in keywords:
            pattern = QRegExp(f"\\b{keyword}\\b(?=\\s*:)")
            self.highlightingRules.append((pattern, keyFormat))

        valuePattern = QRegExp(":\\s*.*$")
        self.highlightingRules.append((valuePattern, valueFormat))

        commentPattern = QRegExp("#.*$")
        self.highlightingRules.append((commentPattern, commentFormat))

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
        self.setTabStopDistance(QFontMetrics(self.font()).horizontalAdvance(' ') * 4)

    def paintEvent(self, event):
        painter = QPainter(self.viewport())
        color = QColor(Qt.lightGray)
        color.setAlpha(50)
        painter.setPen(color)

        fontMetrics = self.fontMetrics()
        spaceWidth = fontMetrics.horizontalAdvance(' ')
        lineHeight = fontMetrics.height()

        block = self.firstVisibleBlock()
        while block.isValid():
            blockY = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
            text = block.text()
            if text:
                spaceCount = len(text) - len(text.lstrip())
                x = spaceCount * spaceWidth
                if x > 0:
                    lineY = blockY + lineHeight // 2
                    painter.drawLine(int(x), int(lineY), int(x), int(lineY + lineHeight))
            block = block.next()

        painter.end()
        super().paintEvent(event)


class FolderHistoryDialog(QDialog):
    def __init__(self, history, parent=None):
        super().__init__(parent)
        self.setWindowTitle("历史目录")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        layout = QVBoxLayout(self)

        info_label = QLabel("选择历史目录或浏览新目录:")
        layout.addWidget(info_label)

        self.list_widget = QListWidget()
        self.list_widget.addItems(history)
        self.list_widget.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.list_widget)

        button_layout = QHBoxLayout()

        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browseFolder)

        select_btn = QPushButton("选择")
        select_btn.clicked.connect(self.accept)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(browse_btn)
        button_layout.addWidget(select_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        self.selected_folder = None

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
        self.maximize_btn = QPushButton("□")
        self.maximize_btn.setFixedSize(24, 24)
        self.maximize_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 16px;
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
        self.highlighter = YamlHighlighter(self.editor.document())
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
        self.loadLastFolder()

    def initUI(self):
        self.setWindowTitle("Nuclei POC 管理工具")
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

        save_button = QPushButton("保存")
        save_button.clicked.connect(self.saveYamlContent)

        exit_button = QPushButton("退出")
        exit_button.clicked.connect(self.close)

        bottom_layout.addWidget(proxy_label)
        bottom_layout.addWidget(self.proxy_input)
        bottom_layout.addWidget(self.dresp_checkbox)
        bottom_layout.addWidget(self.run_button)
        bottom_layout.addWidget(self.batch_button)
        bottom_layout.addWidget(save_button)
        bottom_layout.addWidget(exit_button)

        main_layout.addLayout(bottom_layout)

    def setupTable(self):
        self.tableWidget.setColumnCount(8)
        headers = ['序号', '文件名', '危险等级', '作者', '标签', 'CVE编号', '参考链接', '漏洞描述']
        self.tableWidget.setHorizontalHeaderLabels(headers)

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

    def saveFolderHistory(self, folder_path):
        if not folder_path:
            return

        history = self.loadFolderHistory()
        if folder_path in history:
            history.remove(folder_path)
        history.insert(0, folder_path)
        history = history[:10]

        history_file = os.path.join(os.path.expanduser('~'), '.nuclei_manager_history')
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                for folder in history:
                    f.write(f"{folder}\n")
        except:
            pass

    def loadLastFolder(self):
        if self.folder_history:
            last_folder = self.folder_history[0]
            if os.path.exists(last_folder):
                self.loadFolder(last_folder)

    def selectFolder(self):
        if self.folder_history:
            dialog = FolderHistoryDialog(self.folder_history, self)
            if dialog.exec_() == QDialog.Accepted:
                selected = dialog.selectedFolder()
                if selected and os.path.exists(selected):
                    self.loadFolder(selected)
                    return

        folder = QFileDialog.getExistingDirectory(self, "选择POC目录")
        if folder:
            self.loadFolder(folder)
            self.saveFolderHistory(folder)

    def loadFolder(self, folder_path):
        self.yaml_folder_path = folder_path
        self.yaml_data = []
        self.filtered_yaml_data = []

        try:
            for root, _, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith('.yaml'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                data = yaml.safe_load(content)
                                if isinstance(data, dict):
                                    # 获取相对路径
                                    relative_path = os.path.relpath(file_path, folder_path)
                                    data['original_filename'] = relative_path  # 使用相对路径加文件名
                                    data['file_path'] = file_path
                                    self.yaml_data.append(data)
                        except Exception as e:
                            print(f"加载文件出错 {file}: {str(e)}")

            self.updateTable()
            self.updatePageInfo()
            self.total_files_label.setText(f"POC总数: {len(self.yaml_data)}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载目录失败: {str(e)}")

    def updateTable(self):
        self.tableWidget.setRowCount(0)
        data = self.filtered_yaml_data if self.filtered_yaml_data else self.yaml_data

        start = (self.current_page - 1) * self.rows_per_page
        end = min(start + self.rows_per_page, len(data))

        self.tableWidget.setRowCount(end - start)

        severity_map = {
            'critical': '严重',
            'high': '高危',
            'medium': '中危',
            'low': '低危',
            'info': '信息'
        }

        for row, item in enumerate(data[start:end]):
            info = item.get('info', {})

            self.tableWidget.setItem(row, 0, QTableWidgetItem(str(start + row + 1)))
            self.tableWidget.setItem(row, 1, QTableWidgetItem(item.get('original_filename', '')))  # 这里将显示相对路径

            severity = severity_map.get(info.get('severity', '').lower(), info.get('severity', ''))
            severity_item = QTableWidgetItem(severity)
            if severity == '严重':
                severity_item.setBackground(QColor("#FFE4E1"))
            elif severity == '高危':
                severity_item.setBackground(QColor("#FFF0F5"))
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
                QMessageBox.information(self, "成功", "文件已删除")
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
                QMessageBox.warning(self, "错误", "请选择要运行的POC")
                return

            # 获取当前选中的文件路径
            file_name = self.tableWidget.item(selected_row, 1).text()  # 假定文件名在第二列
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
            # 将目标写入文件
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

            # 生成唯一的临时目录名，并在当前目录下创建
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
                # 创建目标文件的完整路径
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
