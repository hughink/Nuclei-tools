import sys
import os
import uuid
import yaml
import shlex
import shutil
import hashlib
import subprocess
from PyQt5 import QtWidgets
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QPainter, QFontMetrics, QPalette
from PyQt5.QtCore import Qt, QRegExp, QThreadPool
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QVBoxLayout, QHBoxLayout,
                             QWidget, QPushButton, QPlainTextEdit, QMessageBox, QLineEdit, QSplitter, QMenu,
                             QCheckBox, QLabel, QInputDialog)

# author： hugh
# 微信公众号：和光同尘hugh
########################################################################################################################
# 创建一个工作线程类 待开发
# ——————————————————————————————————————————————————————————————————————————————————————————————————————————————————————

########################################################################################################################
# 打开 poc文件
# ——————————————————————————————————————————————————————————————————————————————————————————————————————————————————————
class OpenPOC:
    @staticmethod
    def open_yaml(yaml_folder_path, poc_name):
        # 确保文件名只有一个 '.yaml' 后缀
        if not poc_name.lower().endswith('.yaml'):
            yaml_file_name = poc_name + '.yaml'
        else:
            yaml_file_name = poc_name

        yaml_file_path = os.path.join(yaml_folder_path, yaml_file_name)
        try:
            with open(yaml_file_path, 'r', encoding='utf-8') as yaml_file:
                yaml_content = yaml_file.read()
            return yaml_content
        except Exception as e:
            raise Exception(f"无法打开文件 {yaml_file_name}:\n{e}")

########################################################################################################################

# 1 GUI 主体
# ——————————————————————————————————————————————————————————————————————————————————————————————————————————————————————
# NucleiPOCManager 类用于创建主窗口和表格视图
class NucleiPOCManager(QMainWindow):
    def __init__(self, yaml_data, yaml_folder_path):
        super().__init__()
        self.total_files_label = None
        self.proxy_input = None
        self.target_input = None
        self.batch_button = None
        self.run_button = None
        self.note_editor = None
        self.yamlHighlighter = None
        self.editor = None
        self.goto_page_line_edit = None
        self.page_label = None
        self.search_button = None
        self.tableWidget = None
        self.dresp_checkbox = None
        self.yaml_data = yaml_data
        self.filtered_yaml_data = []  # 初始化为空列表
        self.yaml_folder_path = yaml_folder_path
        self.thread_pool = QThreadPool()  # 创建线程池
        self.temp_dirs = []  # 用于存储临时目录的列表
        self.search_line_edit = QLineEdit()  # 将搜索栏设置为实例变量
        self.current_page = 1

        self.rows_per_page = 50
        # 初始化 search_keyword 为空字符串
        self.search_keyword = ''
        self.total_pages = (len(self.yaml_data) + self.rows_per_page - 1) // self.rows_per_page
        self.yaml_folder_path = yaml_folder_path
        self.initUI()

    def initUI(self):
        self.setWindowTitle("nuclei小工具，由hugh乱写的")
        self.setGeometry(100, 100, 1280, 840)
        palette = QPalette()
        self.setPalette(palette)

        # 创建主布局
        main_layout = QVBoxLayout()

        self.tableWidget = QTableWidget()
        self.tableWidget.setRowCount(23)  # 设置行数为16
        self.tableWidget.setColumnCount(8)  # 增加一列用于放置选中按钮
        self.tableWidget.setHorizontalHeaderLabels(['序号', '文件名', '危害', '作者', 'tags', 'CVE编号', '参考链接', '漏洞描述'])
        self.tableWidget.horizontalHeader().setStretchLastSection(False)
        self.tableWidget.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.tableWidget.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.setShowGrid(True)
        # 设置表格的字体样式和背景颜色
        self.tableWidget.setStyleSheet("""
            QTableWidget {
                background-color: #F3F3F3;  /* 表格的背景色 */
                alternate-background-color: #E8E8E8; /* 用于交替行的背景色 */
                color: #2D2D2D;  /* 字体颜色 */
            }
            QTableWidget::item {
                border-bottom: 1px solid #D7D7D7; /* 单元格下边框线色 */
            }
            QTableWidget::item:selected {
                background-color: #F0A30A;  /* 选中行的背景色 */
                color: #FFFFFF;  /* 选中行的字体色 */
            }
            QHeaderView::section {
                background-color: #9E9E9E;  /* 表头的背景色 */
                color: #2F2F2F;  /* 表头字体颜色 */
                padding-left: 4px;  /* 表头内左填充 */
                border: 1px solid #BFBFBF;  /* 表头边框色 */
                height: 25px;  /* 表头高度 */
            }
        """)

        # 设置表格中的字体大小
        font = self.tableWidget.font()
        font.setPointSize(11)  # 假设您想要设置字体大小为10
        self.tableWidget.setFont(font)

        # 调整行高
        row_height = 20  # 假设每行的高度为20像素
        for row in range(self.tableWidget.rowCount()):
            self.tableWidget.setRowHeight(row, row_height)

        # 为每列设置特定的列宽
        column_widths = [40, 255, 60, 100, 160, 106, 310]  # 为每列指定宽度
        for col, width in enumerate(column_widths):
            self.tableWidget.setColumnWidth(col, width)

        # 设置最后一列宽度自适应
        self.tableWidget.horizontalHeader().setStretchLastSection(True)

        # 设置所有列的大小模式为Fixed，以使用自定义宽度
        for col in range(self.tableWidget.columnCount()):
            self.tableWidget.horizontalHeader().setSectionResizeMode(col, QtWidgets.QHeaderView.Fixed)

        # 禁止单元格内容自动换行
        self.tableWidget.setWordWrap(False)

        # 设置第一列的最小宽度，确保复选框不会被隐藏
        # self.tableWidget.setColumnWidth(0, 50)  # 第一列宽度设置为50像素

        # 设置表格的整体高度
        table_height = row_height * 23
        self.tableWidget.setMinimumHeight(table_height)

        # 添加表格到主布局
        main_layout.addWidget(self.tableWidget)

        # 创建搜索栏和搜索按钮
        self.search_line_edit = QLineEdit()
        self.search_line_edit.setPlaceholderText("全局搜索")
        # 设置清除按钮显示，当编辑框中有内容时
        self.search_line_edit.setClearButtonEnabled(True)
        # 不再设置固定宽度
        # self.search_line_edit.setFixedWidth(800)  # 不需要设置固定宽度
        self.search_button = QPushButton('搜索')

        # 统计 YAML 文件数量
        yaml_files_count = self.count_yaml_files()

        # 创建一个 QLabel 对象来显示 YAML 文件总数
        self.total_files_label = QLabel(f"【POC数 / {yaml_files_count} 】", self)

        # 分页控件
        self.page_label = QLabel()
        reset_search_button = QPushButton('刷新')
        prev_page_button = QPushButton('上一页')
        next_page_button = QPushButton('下一页')
        self.goto_page_line_edit = QLineEdit()  # 创建跳转到页码的输入框
        self.goto_page_line_edit.setPlaceholderText("页码")
        self.goto_page_line_edit.setFixedWidth(40)
        goto_page_button = QPushButton('跳转')

        # 创建一个新的水平布局来包含搜索栏、搜索按钮和分页按钮
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.search_line_edit)  # 添加搜索栏，并设置拉伸因子为1
        top_layout.addWidget(self.search_button)  # 添加搜索按钮
        top_layout.addWidget(reset_search_button)  # 添加重置搜索按钮
        top_layout.addWidget(prev_page_button)  # 添加上一页按钮
        top_layout.addWidget(self.page_label)  # 添加页码标签
        top_layout.addWidget(next_page_button)  # 添加下一页按钮
        top_layout.addWidget(self.goto_page_line_edit)  # 添加跳转到页码的输入框
        top_layout.addWidget(goto_page_button)  # 添加跳转按钮
        top_layout.addWidget(self.total_files_label)

        # 将新的顶部布局添加到主布局
        main_layout.addLayout(top_layout)

        # 连接搜索按钮的点击事件
        self.search_button.clicked.connect(lambda: self.search_table(self.search_line_edit.text()))

        # 连接清除按钮的信号与槽，以便在点击时执行清空操作
        self.search_line_edit.textChanged.connect(self.on_search_text_changed)

        # 设置表格的上下文菜单策略并连接信号：
        self.tableWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableWidget.customContextMenuRequested.connect(self.table_widget_context_menu)

        # 连接按钮的点击事件
        prev_page_button.clicked.connect(self.prev_page)
        next_page_button.clicked.connect(self.next_page)
        goto_page_button.clicked.connect(self.goto_page)
        reset_search_button.clicked.connect(self.reset_search)  # 绑定重置搜索的事件处理函数

        # 分页布局
        pagination_layout = QHBoxLayout()
        pagination_layout.addStretch(1)  # 添加弹性空间，推动控件靠右显示
        pagination_layout.addWidget(reset_search_button)  # 将重置搜索按钮添加到分页布局
        pagination_layout.addWidget(prev_page_button)  # 添加上一页按钮到分页布局
        pagination_layout.addWidget(self.page_label)   # 添加页码标签到分页布局
        pagination_layout.addWidget(next_page_button)  # 添加下一页按钮到分页布局
        pagination_layout.addWidget(self.goto_page_line_edit)  # 跳转到页码的输入框到分页布局
        pagination_layout.addWidget(goto_page_button)  # 跳转按钮到分页布局
        pagination_layout.addWidget(self.total_files_label)  # 添加文件总数标签到分页布局

        # 创建一个水平分割器
        splitter = QSplitter(Qt.Horizontal)

        # 创建左侧的目标输入框
        self.target_input = QPlainTextEdit()
        self.target_input.setReadOnly(False)  # 设置目标输入框为可编辑
        self.target_input.setStyleSheet("""QPlainTextEdit {background-color: #FFFFFF; color: #000000; } """)

        splitter.addWidget(self.target_input)  # 添加目标输入框到分割器

        # 创建编辑器设置
        self.editor = YamlTextEdit()  # 使用自定义的 YamlTextEdit
        self.editor.setReadOnly(False)  # 设置编辑器为可编辑
        editor_font = self.editor.font()
        editor_font.setPointSize(12)
        self.editor.setFont(editor_font)
        # 设置编辑器的背景色和字体颜色
        self.editor.setStyleSheet(
            "QPlainTextEdit {background-color: #272822; color: #F8F8F2; font-family: 'Courier New'; font-size: 12pt;}")
        # 编辑器高度设置
        row_height = 20
        editor_height = row_height * 25  # 20行的高度
        self.editor.setFixedHeight(editor_height)
        splitter.addWidget(self.editor)  # 先添加编辑器到分割器
        # 应用高亮显示
        self.yamlHighlighter = YamlHighlighter(self.editor.document())

        # 设置左右编辑器的宽度比例为2:8
        total_width = splitter.width()  # 获取分割器的总宽度
        left_width = total_width * 2 // 10  # 计算左侧编辑器的宽度
        right_width = total_width - left_width  # 计算右侧编辑器的宽度
        splitter.setSizes([left_width, right_width])

        # 添加分割器到主布局
        main_layout.addWidget(splitter)

        ''' 底部按钮布局，包括扫描目标，参数选择，代理，保存、退出 '''
        # 创建水平布局用于扫描目标、--dresp、代理和运行按钮
        scan_layout = QHBoxLayout()

        # 创建提示标题
        target_input_label = QLabel(" 在上方空白输入框内输入目标，一行一个。    代理：")
        scan_layout.addWidget(target_input_label)  # 将提示标签添加至水平布局

        # 创建代理设置输入框
        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText("请输入代理地址 (例如 http://127.0.0.1:8080)")
        self.proxy_input.setClearButtonEnabled(True)  # 启用清除按钮
        scan_layout.addWidget(self.proxy_input)

        # 创建 --dresp 勾选框
        self.dresp_checkbox = QCheckBox("细节")
        scan_layout.addWidget(self.dresp_checkbox)

        # 创建运行按钮
        self.run_button = QPushButton("运行")
        self.run_button.clicked.connect(self.run_nuclei)
        scan_layout.addWidget(self.run_button)

        # 创建批量按钮
        self.batch_button = QPushButton("批量运行")
        self.batch_button.clicked.connect(self.run_nuclei_batch)  # 绑定按钮点击事件到新的处理函数
        scan_layout.addWidget(self.batch_button)

        # 创建保存按钮
        save_button = QPushButton('保存')
        save_button.clicked.connect(self.save_yaml_content)
        scan_layout.addWidget(save_button)

        # 创建退出按钮
        exit_button = QPushButton('退出')
        exit_button.clicked.connect(self.close)
        scan_layout.addWidget(exit_button)

        # 将扫描布局添加到主布局
        main_layout.addLayout(scan_layout)
        ''' 底部按钮布局，包括扫描目标，参数选择，代理，保存、退出 '''

        # 当点击表格的某一行时，尝试显示该行对应的YAML文件内容
        self.tableWidget.cellClicked.connect(self.on_table_cell_clicked)

        # 设置中心窗口
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        self.populate_table()  # 使用新的分页填充函数

# 1 GUI 主体
# ——————————————————————————————————————————————————————————————————————————————————————————————————————————————————————

########################################################################################################################
# 2 方法部分
# ——————————————————————————————————————————————————————————————————————————————————————————————————————————————————————
    def populate_table(self):
        # 清除表格内容
        self.tableWidget.clearContents()

        # 如果没有搜索结果且搜索关键词不为空，则只显示“未找到任何内容”的消息
        if not self.filtered_yaml_data and self.search_keyword:
            self.tableWidget.setRowCount(1)
            no_data_item = QTableWidgetItem("未找到任何内容")
            no_data_item.setFlags(Qt.ItemIsEnabled)  # 设置为不可编辑
            self.tableWidget.setItem(0, 0, no_data_item)
            # 合并单元格以填充消息
            self.tableWidget.setSpan(0, 0, 1, self.tableWidget.columnCount())
            return  # 早期返回，不显示其他数据

        # 使用 filtered_yaml_data 如果有搜索结果，否则使用 yaml_data
        data_to_display = self.filtered_yaml_data if self.filtered_yaml_data else self.yaml_data
        self.tableWidget.clearContents()
        self.tableWidget.setRowCount(min(self.rows_per_page, len(data_to_display) - (self.current_page - 1) * self.rows_per_page))
        start = (self.current_page - 1) * self.rows_per_page
        end = min(start + self.rows_per_page, len(data_to_display))
        # 创建一个映射字典，将英文的严重性等级映射到中文
        severity_mapping = {
            'critical': '严重',
            'high': '高危',
            'medium': '中危',
            'low': '低危',
            'info': '信息'
        }
        for table_row, data_idx in enumerate(range(start, end)):
            item = data_to_display[data_idx]  # 使用 data_to_display 获取当前项
            # 检查item是否为字典类型
            if isinstance(item, dict):
                # 使用原始的 YAML 文件名，如果不存在则使用 'N/A.yaml'
                name = item.get('original_filename', item.get('id', "N/A") + ".yaml")
                info = item.get('info', {})
                # 获取严重性等级并翻译成中文
                severity_english = info.get('severity', "N/A")
                severity = severity_mapping.get(severity_english.lower(),
                                                severity_english)  # 使用映射字典获取中文等级，如果没有匹配则使用原英文等级

                # 从嵌套的字典中安全地提取 cve-id
                classification = info.get('classification', {})
                cve_id = classification.get('cve-id', "N/A") if classification else "N/A"

                author = info.get('author', "N/A")
                tags = info.get('tags', "N/A")
                description = info.get('description', "N/A")

                # 处理 reference 字段，确保即使它不是列表也能正确提取第一个链接
                reference = info.get('reference')
                if isinstance(reference, list) and reference:
                    reference_url = reference[0]  # 获取列表中的第一个链接
                elif isinstance(reference, str):
                    reference_url = reference  # 直接获取字符串链接
                else:
                    reference_url = "N/A"  # 如果 reference 字段不是列表或字符串
            else:
                # 如果item不是字典类型
                name = "N/A.yaml"
                severity = "N/A"
                author = "N/A"
                tags = "N/A"
                description = "N/A"
                reference_url = "N/A"
                cve_id = "N/A"

            # 设置单元格项
            table_item = QTableWidgetItem(str(data_idx + 1))
            table_item.setTextAlignment(Qt.AlignCenter)  # 设置文本居中对齐
            self.tableWidget.setItem(table_row, 0, table_item)

            self.tableWidget.setItem(table_row, 1, QTableWidgetItem(name))

            table_item = QTableWidgetItem(severity)
            table_item.setTextAlignment(Qt.AlignCenter)  # 设置文本居中对齐
            self.tableWidget.setItem(table_row, 2, table_item)

            self.tableWidget.setItem(table_row, 3, QTableWidgetItem(author))

            self.tableWidget.setItem(table_row, 4, QTableWidgetItem(tags))
            self.tableWidget.setItem(table_row, 5, QTableWidgetItem(cve_id))
            self.tableWidget.setItem(table_row, 6, QTableWidgetItem(reference_url))
            self.tableWidget.setItem(table_row, 7, QTableWidgetItem(description))

        # 校正总行数，最后一页可能没有完整的 rows_per_page 行
        current_total_rows = end - start
        if current_total_rows < self.rows_per_page:
            self.tableWidget.setRowCount(current_total_rows)

    # 刷新表格中展示的内容
    def refresh_table_row(self, row, yaml_data, file_name=None):
        # 假设 yaml_data 是一个字典，包含 'info' 键和 'id' 键
        # 创建一个映射字典，将英文的严重性等级映射到中文
        severity_mapping = {
            'critical': '严重',
            'high': '高危',
            'medium': '中危',
            'low': '低危',
            'info': '信息'
        }
        if isinstance(yaml_data, dict):
            # 如果提供了文件名，则使用它，否则尝试从 yaml_data 中获取 'original_filename'
            # 如果 'original_filename' 不存在，则使用 'id' 键的值加上 '.yaml'
            name = file_name or yaml_data.get('original_filename', yaml_data.get('id', "N/A") + ".yaml")
            info = yaml_data.get('info', {})
            severity_english = info.get('severity', "N/A")
            severity = severity_mapping.get(severity_english.lower(), severity_english)  # 使用映射字典获取中文等级，如果没有匹配则使用原英文等级

            # 从嵌套的字典中安全地提取 cve-id
            classification = info.get('classification', {})
            cve_id = classification.get('cve-id', "N/A") if classification else "N/A"

            author = info.get('author', "N/A")
            tags = info.get('tags', "N/A")
            description = info.get('description', "N/A")
            # 处理 reference 字段，确保即使它不是列表也能正确提取第一个链接
            reference = info.get('reference')
            if isinstance(reference, list) and reference:
                reference_url = reference[0]  # 获取列表中的第一个链接
            elif isinstance(reference, str):
                reference_url = reference  # 直接获取字符串链接
            else:
                reference_url = "N/A"  # 如果 reference 字段不是列表或字符串

            # 确保 tags 是一个字符串
            if isinstance(tags, list):
                tags = ', '.join(tags)  # 使用逗号和空格来分隔标签
            elif not isinstance(tags, str):
                tags = "N/A"  # 如果 tags 既不是列表也不是字符串，则设置为 "N/A"

            # 使用 textwrap 填充描述，以便它在表格中更好地显示
            from textwrap import fill
            description = fill(description, width=50)

            # 设置单元格项
            table_item = QTableWidgetItem(str(row + 1))
            table_item.setTextAlignment(Qt.AlignCenter)  # 设置文本居中对齐
            self.tableWidget.setItem(row, 0, table_item)

            self.tableWidget.setItem(row, 1, QTableWidgetItem(name))

            table_item = QTableWidgetItem(severity)
            table_item.setTextAlignment(Qt.AlignCenter)  # 设置文本居中对齐
            self.tableWidget.setItem(row, 2, table_item)

            self.tableWidget.setItem(row, 3, QTableWidgetItem(author))
            self.tableWidget.setItem(row, 4, QTableWidgetItem(tags))
            self.tableWidget.setItem(row, 5, QTableWidgetItem(cve_id))
            self.tableWidget.setItem(row, 6, QTableWidgetItem(reference_url))
            self.tableWidget.setItem(row, 7, QTableWidgetItem(description))

    # 刷新页码
    def update_page_label(self):
        self.page_label.setText(f'Page {self.current_page} of {self.total_pages}')

    # 统计 yaml_folder_path 文件夹下 yaml 文件的数量
    def count_yaml_files(self):
        yaml_files_count = len([name for name in os.listdir(self.yaml_folder_path)
                                if os.path.isfile(os.path.join(self.yaml_folder_path, name)) and name.lower().endswith('.yaml')])
        return yaml_files_count

    # 重新计算文件数量
    def update_file_count_label(self):
        yaml_files_count = self.count_yaml_files()
        # 更新文件总数标签
        self.total_files_label.setText(f"【{yaml_files_count} pocs】")

    # 全局搜索方法
    def search_table(self, keyword):
        # 清空过滤后的数据
        self.filtered_yaml_data.clear()
        # 保存搜索关键词
        self.search_keyword = keyword
        # 如果关键词不为空，则进行搜索
        if keyword:
            # 分割关键词，支持 'AND' 和 'OR' 操作
            keywords = keyword.split(' ')
            if 'AND' in keywords:
                # 使用 'AND' 逻辑运算符进行搜索
                keywords.remove('AND')
                self.filtered_yaml_data = [item for item in self.yaml_data if all(kw.lower() in yaml.dump(item, allow_unicode=True).lower() for kw in keywords)]
            elif 'OR' in keywords:
                # 使用 'OR' 逻辑运算符进行搜索
                keywords.remove('OR')
                self.filtered_yaml_data = [item for item in self.yaml_data if any(kw.lower() in yaml.dump(item, allow_unicode=True).lower() for kw in keywords)]
            else:
                # 默认情况下，使用 'AND' 逻辑运算符进行搜索
                self.filtered_yaml_data = [item for item in self.yaml_data if all(kw.lower() in yaml.dump(item, allow_unicode=True).lower() for kw in keywords)]
        else:
            # 如果没有关键词，则显示所有数据
            self.filtered_yaml_data = self.yaml_data.copy()

        # 重置到第一页
        self.current_page = 1
        # 重新计算总页数
        self.total_pages = max(1, (len(self.filtered_yaml_data) + self.rows_per_page - 1) // self.rows_per_page)
        # 更新表格和分页标签
        self.populate_table()
        self.update_page_label()

    # 当搜索框被清空时，执行搜索以重置表格内容
    def on_search_text_changed(self, text):
        if text == "":
            self.search_table(text)

    # 当点击表格的某一行时，尝试显示该行对应的YAML文件内容
    def on_table_cell_clicked(self, row):
        poc_name = self.tableWidget.item(row, 1).text()
        # 确保文件名只有一个 '.yaml' 后缀
        if poc_name.lower().endswith('.yaml'):
            poc_name = poc_name[:-5]  # 移除 '.yaml' 后缀
        if poc_name != "N/A":
            try:
                yaml_content = OpenPOC.open_yaml(self.yaml_folder_path, poc_name)
                self.editor.setPlainText(yaml_content)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法打开文件 {poc_name}.yaml:\n{e}")
        else:
            QMessageBox.warning(self, "警告", "无效的文件名。")

    # 重置搜索栏
    def reset_search(self):
        self.search_line_edit.setText('')
        # 清空过滤后的数据
        self.filtered_yaml_data = []  # 重置为一个空列表
        # 重置到第一页
        self.current_page = 1
        # 重新计算总页数
        self.total_pages = (len(self.yaml_data) + self.rows_per_page - 1) // self.rows_per_page
        # 更新表格和分页标签
        self.populate_table()
        self.update_page_label()
        self.update_table_after_deletion()  # 调用新方法来刷新表格

    # 上一页
    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.populate_table()
            self.update_page_label()

    # 下一页
    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.populate_table()
            self.update_page_label()

    # 跳转到指定页
    def goto_page(self):
        # 从输入框读取页码并跳转到指定页数
        page_number_text = self.goto_page_line_edit.text().strip()  # 去除可能的前后空白字符

        if not page_number_text.isdigit():  # 检查输入是否为数字
            QMessageBox.warning(self, "警告", "请输入有效的页码数字。")
            return

        page_number = int(page_number_text)  # 将输入转换为整数

        if 1 <= page_number <= self.total_pages:
            self.current_page = page_number
            self.populate_table()
            self.update_page_label()
        else:
            QMessageBox.warning(self, "警告", "输入的页码超出范围。")

    # 使用系统自带的命令行窗口执行Nuclei
    def run_nuclei(self):
        targets = self.target_input.toPlainText().strip()
        if targets:
            # 将目标保存到临时文件
            temp_file_path = self.save_targets_file(targets)

            # 检查是否有行被选中
            selected_items = self.tableWidget.selectedItems()
            if selected_items:
                # 获取当前选中的行
                selected_row = self.tableWidget.currentRow()
                file_name = self.tableWidget.item(selected_row, 1).text()  # 假定文件名在第二列
                file_path = os.path.join(self.yaml_folder_path, file_name)

                # 构建Nuclei命令
                cmd = ["nuclei", "-t", file_path, "-l", temp_file_path]
                if self.dresp_checkbox.isChecked():
                    cmd.append("--dresp")
                if self.proxy_input.text():
                    cmd.extend(["-proxy", self.proxy_input.text()])

                self.execute_command_in_terminal(cmd)
            else:
                QMessageBox.warning(self, "选择错误", "请在列表中选择一个要扫描的文件。")
        else:
            QMessageBox.warning(self, "输入错误", "请输入有效的扫描目标。")

    # 保存目标到临时文件
    def save_targets_file(self, targets):
        # 获取yaml_folder_path的父目录
        parent_dir = os.path.dirname(self.yaml_folder_path)
        # 在父目录中创建targets.txt文件的路径
        temp_file_path = os.path.join(parent_dir, "targets.txt")
        # 将目标写入文件
        with open(temp_file_path, 'w') as file:
            file.write(targets)
        return temp_file_path

    # 使用系统自带的命令行窗口执行多个POC
    def run_nuclei_batch(self):
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

        # 生成唯一的临时目录名
        unique_temp_dir_name = str(uuid.uuid4())
        temp_dir_path = os.path.join(os.path.dirname(self.yaml_folder_path), 'temp', unique_temp_dir_name)

        # 确保临时目录存在
        if not os.path.exists(temp_dir_path):
            os.makedirs(temp_dir_path)

        # 如果已经有一个临时目录在列表中，删除它
        if len(self.temp_dirs) > 0:
            previous_temp_dir = self.temp_dirs.pop(0)  # 获取并移除列表中的第一个元素
            if os.path.exists(previous_temp_dir):
                shutil.rmtree(previous_temp_dir)

        # 将新的临时目录添加到列表中
        self.temp_dirs.append(temp_dir_path)

        try:
            # 复制文件到临时目录
            for file_name in file_names:
                source_path = os.path.join(self.yaml_folder_path, file_name)
                destination_path = os.path.join(temp_dir_path, file_name)
                shutil.copy(source_path, destination_path)

            # 构建 Nuclei 命令
            cmd = ["nuclei", "-t", temp_dir_path, "-l", temp_file_path]
            if self.dresp_checkbox.isChecked():
                cmd.append("--dresp")
            if self.proxy_input.text():
                cmd.extend(["-proxy", self.proxy_input.text()])

            # 使用系统自带的命令行窗口执行命令
            self.execute_command_in_terminal(cmd)

        except Exception as e:
            QMessageBox.critical(self, "运行错误", f"运行 Nuclei 时发生错误:\n{e}")

    # 再次启动批量扫描时，删除上一次批量扫描的临时文件
    def cleanup_temp_dir(self, temp_dir_path):
        # 清理指定的临时目录
        if os.path.exists(temp_dir_path):
            shutil.rmtree(temp_dir_path)  # 使用 shutil.rmtree 安全删除目录树
        # 从列表中移除已清理的目录
        if temp_dir_path in self.temp_dirs:
            self.temp_dirs.remove(temp_dir_path)

    # 根据不同的操作系统执行命令
    def execute_command_in_terminal(self, cmd):
        try:
            if sys.platform == 'win32':  # Windows
                subprocess.Popen(["start", "cmd", "/k"] + cmd, shell=True)
            elif sys.platform == 'darwin':  # macOS
                # 将命令列表转换为一个转义后的字符串
                escaped_command = ' '.join(map(shlex.quote, cmd))
                script = f'tell application "Terminal" to do script "{escaped_command}"'
                subprocess.Popen(['osascript', '-e', script])
            elif sys.platform == 'linux':  # Linux
                # 将命令列表转换为一个转义后的字符串
                terminal_cmd = ' '.join(map(shlex.quote, cmd))
                subprocess.Popen(['x-terminal-emulator', '-e', f'bash -c "{terminal_cmd}; exec bash"'])
        except Exception as e:
            QMessageBox.critical(self, "运行错误", f"运行命令时发生错误:\n{e}")

    # 在线新增，修改poc后保存
    def save_yaml_content(self):
        # 获取编辑器中的内容
        yaml_content = self.editor.toPlainText()
        if not yaml_content.strip():
            QMessageBox.warning(self, "警告", "编辑器内容为空，无法保存。")
            return

        # 计算当前编辑器内容的哈希值
        current_content_hash = hashlib.md5(yaml_content.encode('utf-8')).hexdigest()

        selected_row = self.tableWidget.currentRow()
        is_new_file = selected_row < 0  # 如果没有选中的行，则为新文件

        if not is_new_file:
            # 选中了表格中的文件，更新该文件
            file_name = self.tableWidget.item(selected_row, 1).text()  # 假设第二列包含文件名
        else:
            # 没有选中表格中的文件，提示用户输入新的文件名
            file_name, ok = QInputDialog.getText(self, "保存文件", "请输入文件名:", QLineEdit.Normal, "")
            if not ok or not file_name.strip():
                QMessageBox.warning(self, "取消操作", "文件未保存。")
                return
            if not file_name.endswith('.yaml'):
                file_name += '.yaml'

            # 检查文件名是否重复
            for i in range(self.tableWidget.rowCount()):
                existing_file_name = self.tableWidget.item(i, 1).text()
                if file_name == existing_file_name:
                    QMessageBox.warning(self, "错误", "文件名已存在。")
                    return

        # 检查文件内容是否重复
        for i in range(self.tableWidget.rowCount()):
            table_item = self.tableWidget.item(i, 1)
            if table_item is not None:  # 确保 table_item 不是 None
                existing_file_name = table_item.text()
                existing_file_path = os.path.join(self.yaml_folder_path, existing_file_name)
                with open(existing_file_path, 'r', encoding='utf-8') as existing_file:
                    existing_content = existing_file.read()
                    existing_content_hash = hashlib.md5(existing_content.encode('utf-8')).hexdigest()
                    if current_content_hash == existing_content_hash and existing_file_name != file_name:
                        QMessageBox.warning(self, "错误", "已存在具有相同内容的文件。")
                        return

        # 保存文件内容
        yaml_path = os.path.join(self.yaml_folder_path, file_name)
        try:
            with open(yaml_path, 'w', encoding='utf-8') as file:
                file.write(yaml_content)
            QMessageBox.information(self, "保存成功", f"文件 '{file_name}' 已成功保存。")
            yaml_data_dict = yaml.safe_load(yaml_content)
            if is_new_file:
                # 添加新文件到内部数据结构
                self.yaml_data.append(yaml_data_dict)
                # 添加新文件到表格
                self.add_new_row_to_table(file_name, yaml_content)
                # 更新文件总数
                self.update_file_count_label()
            else:
                # 更新现有条目
                self.yaml_data[selected_row] = yaml_data_dict
                # 更新表格中的文件名
                self.tableWidget.item(selected_row, 1).setText(file_name)
                # 刷新表格行
                self.refresh_table_row(selected_row, yaml_data_dict)
            # 重新加载表格数据
            self.populate_table()
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存文件时发生错误:\n{e}")

    # 解析 YAML 内容以获取数据
    def add_new_row_to_table(self, file_name, yaml_content):
        try:
            yaml_data = yaml.safe_load(yaml_content)
            # 添加到 self.yaml_data 列表
            self.yaml_data.append(yaml_data)
            # 如果当前是在搜索结果中添加，也更新搜索结果列表
            self.filtered_yaml_data.append(yaml_data)
            # 更新表格
            self.populate_table()
            # 更新表格中的文件名
            last_row = self.tableWidget.rowCount() - 1
            self.refresh_table_row(last_row, yaml_data, file_name)
            # 文件添加后，更新文件总数
            self.update_file_count_label()
        except yaml.YAMLError as e:
            QMessageBox.critical(self, "解析错误", f"解析 YAML 内容时发生错误:\n{e}")

    # 供删除调用的更新方法
    def update_table_after_deletion(self):
        # 清除表格内容并设置新的行数
        self.tableWidget.clearContents()
        self.tableWidget.setRowCount(len(self.yaml_data))

        # 遍历 yaml_data，更新表格
        for row, yaml_entry in enumerate(self.yaml_data):
            self.refresh_table_row(row, yaml_entry)

    # 文件名列的右键菜单
    def table_widget_context_menu(self, position):
        menu = QMenu()

        # 添加菜单项
        copy_name_action = menu.addAction("复制文件名")
        copy_path_action = menu.addAction("拷贝文件路径")
        delete_action = menu.addAction("删除文件")  # 添加删除菜单项

        # 获取选中的项
        selected_item = self.tableWidget.itemAt(position)
        if selected_item is None:
            return

        # 获取当前行
        row = selected_item.row()

        # 显示菜单并等待用户选择动作
        action = menu.exec_(self.tableWidget.viewport().mapToGlobal(position))

        # 如果选择了复制文件名
        if action == copy_name_action:
            file_name = self.tableWidget.item(row, 1).text()  # 假设文件名在第二列
            QApplication.clipboard().setText(file_name)

        # 如果选择了拷贝文件路径
        elif action == copy_path_action:
            file_name = self.tableWidget.item(row, 1).text()  # 假设文件名在第二列
            file_path = os.path.join(self.yaml_folder_path, file_name)
            QApplication.clipboard().setText(file_path)

        # 如果选择了删除
        elif action == delete_action:
            file_name = self.tableWidget.item(row, 1).text()
            file_path = os.path.join(self.yaml_folder_path, file_name)

            # 弹出确认对话框
            reply = QMessageBox.question(self, '确认删除', f"你确定要删除文件 {file_name} 吗?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

            if reply == QMessageBox.Yes:
                try:
                    os.remove(file_path)  # 从文件系统中删除文件
                    # 从存储数据的结构中移除对应的数据项
                    self.yaml_data = [data for data in self.yaml_data if
                                      data.get('original_filename', data.get('id', '') + ".yaml") != file_name]
                    self.update_table_after_deletion()  # 调用新方法来刷新表格
                    # 文件添加后，更新文件总数
                    self.update_file_count_label()
                except OSError as e:
                    QMessageBox.critical(self, '删除失败', f"无法删除文件 {file_name}: {e}")

# 2 方法部分
# ——————————————————————————————————————————————————————————————————————————————————————————————————————————————————————


########################################################################################################################
# 3 编辑器美化
# ——————————————————————————————————————————————————————————————————————————————————————————————————————————————————————
# 缩进辅助线
class YamlTextEdit(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 设置 Tab 宽度为 4 个空格的等效宽度
        self.setTabStopDistance(QFontMetrics(self.font()).horizontalAdvance(' ') * 4)

    def paintEvent(self, event):
        painter = QPainter(self.viewport())
        color = QColor(Qt.lightGray)  # 缩进线颜色
        color.setAlpha(50)  # 透明度
        painter.setPen(color)

        fontMetrics = self.fontMetrics()
        spaceWidth = fontMetrics.horizontalAdvance(' ')  # 空格宽度
        lineHeight = fontMetrics.height()  # 行高

        # 返回所有可见行范围
        block = self.firstVisibleBlock()
        while block.isValid():
            blockY = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
            text = block.text()
            if text:
                spaceCount = 0  # 数空格数
                for char in text:
                    if char == ' ':
                        spaceCount += 1
                    elif char == '\t':
                        # 假设每个 Tab 等于 4 个空格
                        spaceCount += 4
                    else:
                        break
                x = spaceCount * spaceWidth
                if x > 0:
                    lineY = blockY + lineHeight // 2
                    painter.drawLine(int(x), int(lineY), int(x), int(lineY + lineHeight))  # 画线
            block = block.next()

        painter.end()
        super().paintEvent(event)

# yaml poc 文本高亮显示
class YamlHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlightingRules = []

        # 定义键的高亮格式
        keyFormat = QTextCharFormat()
        keyFormat.setForeground(QColor("#1E90FF"))  # 深蓝色
        keyFormat.setFontWeight(QFont.Bold)

        # 定义值的高亮格式
        valueFormat = QTextCharFormat()
        valueFormat.setForeground(QColor("#32CD32"))  # 亮绿色

        # 定义注释的高亮格式
        commentFormat = QTextCharFormat()
        commentFormat.setForeground(QColor("#B22222"))  # 暗红色

        # 定义需要高亮的关键词列表
        keywords = ['id', 'info', 'name', 'author', 'metadata', 'fofa-query', '360-query', 'hunter-query', 'verified',
                    'severity', 'tags', 'description', 'requests', 'matchers', 'type', 'POST', 'GET', 'PUT', 'reference',
                    'max-request', 'http', 'regex', 'dsl', 'extractors']

        # 为每个关键词创建一个正则表达式，并添加到规则中
        for keyword in keywords:
            pattern = QRegExp(f"\\b{keyword}\\b(?=\\s*:)")
            self.highlightingRules.append((pattern, keyFormat))

        # 添加值的高亮规则
        valuePattern = QRegExp(":\\s*.*$")
        self.highlightingRules.append((valuePattern, valueFormat))

        # 添加注释的高亮规则
        commentPattern = QRegExp("#.*$")
        self.highlightingRules.append((commentPattern, commentFormat))

    def highlightBlock(self, text):
        # 应用每条高亮规则
        for pattern, format in self.highlightingRules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)
        self.setCurrentBlockState(0)
# 编辑器美化
# ——————————————————————————————————————————————————————————————————————————————————————————————————————————————————————


########################################################################################################################
# 加载 YAML 文件并转换为所需的数据结构
# ——————————————————————————————————————————————————————————————————————————————————————————————————————————————————————
def load_yaml_files(yaml_folder):
    yaml_data = []
    for dirpath, dirnames, files in os.walk(yaml_folder):
        for file_name in files:
            if file_name.lower().endswith('.yaml'):
                yaml_file_path = os.path.join(dirpath, file_name)
                try:
                    with open(yaml_file_path, 'r', encoding='utf-8') as yaml_file:
                        data = yaml.safe_load(yaml_file)
                        # 将原始文件名添加到数据中，以便在表格视图中使用
                        data['original_filename'] = file_name
                        yaml_data.append(data)
                except Exception as e:
                    print(f'Error loading {file_name}: {e}')
    return yaml_data
# 加载 YAML 文件并转换为所需的数据结构
# ——————————————————————————————————————————————————————————————————————————————————————————————————————————————————————

# 加载 包含 YAML 文件夹的路径
# ——————————————————————————————————————————————————————————————————————————————————————————————————————————————————————
def get_yaml_folder_path():
    app = QApplication(sys.argv)  # 创建 QApplication 实例
    while True:
        inputDialog = QInputDialog()  # 创建 QInputDialog 实例
        inputDialog.setWindowTitle('欢迎使用🙋！')
        inputDialog.setLabelText('请输入 nuclei-poc文件所在的目录路径(搜索poc在同一目录，目录下不能有子文件夹哦！):')
        inputDialog.setInputMode(QInputDialog.TextInput)  # 设置输入模式为文本输入
        # 设置对话框的大小
        inputDialog.resize(600, 100)  # 设置输入窗口的宽度和高度

        ok = inputDialog.exec_()
        text = inputDialog.textValue().strip()

        if ok:
            folder_path = text
            # 检查路径是否存在
            if not os.path.exists(folder_path):
                QMessageBox.warning(None, "路径不存在", "输入的路径不存在，请重新输入。")
                continue

            # 检查路径下是否有子文件夹
            if any(os.path.isdir(os.path.join(folder_path, i)) for i in os.listdir(folder_path)):
                QMessageBox.warning(None, "存在子文件夹", "输入的路径包含子文件夹，请重新输入没有子文件夹的路径。")
                continue

            return folder_path
        else:
            QMessageBox.warning(None, "未输入路径", "欢迎下次使用")
            sys.exit()

########################################################################################################################
# 运行应用程序的主函数
#  ————————————————————————————————————————————————————————————————————————————————————————————————————————————————————
def main():
    yaml_folder_path = get_yaml_folder_path()  # 获取 YAML 文件目录
    app = QApplication(sys.argv)
    yaml_data = load_yaml_files(yaml_folder_path)  # 加载 YAML 文件数据
    ex = NucleiPOCManager(yaml_data, yaml_folder_path)
    ex.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
