#!/usr/bin/env python3
import sys
import time
from collections import Counter, defaultdict
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QWidget, QLabel, QPlainTextEdit, QPushButton, QTabWidget,
                             QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
                             QMessageBox, QCheckBox, QProgressBar, QFileDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QThread

class TextLoaderThread(QThread):
    progress_updated = pyqtSignal(int)
    loading_complete = pyqtSignal(str)

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.text = text

    def run(self):
        lines = self.text.split('\n')
        total_lines = len(lines)
        chunk_size = 50000
        result = []

        for i in range(0, total_lines, chunk_size):
            chunk = '\n'.join(lines[i:i+chunk_size])
            result.append(chunk)
            progress = min(100, int((i + chunk_size) / total_lines * 100))
            self.progress_updated.emit(progress)

        self.loading_complete.emit('\n'.join(result))

class CopyableTableWidget(QTableWidget):
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_C and event.modifiers() == Qt.ControlModifier:
            self.copy_selected_rows()
        else:
            super().keyPressEvent(event)

    def copy_selected_rows(self):
        selected_ranges = self.selectedRanges()
        if not selected_ranges:
            return

        clipboard = QApplication.clipboard()
        copied_text = ""

        for r in range(selected_ranges[0].topRow(), selected_ranges[0].bottomRow() + 1):
            row_data = []
            for c in range(selected_ranges[0].leftColumn(), selected_ranges[0].rightColumn() + 1):
                item = self.item(r, c)
                row_data.append(item.text() if item else "")
            copied_text += "\t".join(row_data) + "\n"

        if copied_text:
            clipboard.setText(copied_text.strip())

class CompareThread(QThread):
    progress_signal = pyqtSignal(int, str)  # 进度百分比 + 状态提示
    finished_signal = pyqtSignal(dict, dict, dict, dict, float)

    def __init__(self, orig_a, cmp_a, orig_b, cmp_b, parent=None):
        super().__init__(parent)
        self.orig_a = orig_a
        self.cmp_a = cmp_a
        self.orig_b = orig_b
        self.cmp_b = cmp_b

    def run(self):
        start = time.time()

        self.progress_signal.emit(10, "Start analyzing list A...")
        set_a, dup_a = self.analyze(self.orig_a, self.cmp_a)
        self.progress_signal.emit(40, "Start analyzing list B...")
        set_b, dup_b = self.analyze(self.orig_b, self.cmp_b)

        self.progress_signal.emit(60, "Building mapping relationships...")
        map_a = self.build_map(self.orig_a, self.cmp_a)
        map_b = self.build_map(self.orig_b, self.cmp_b)

        self.progress_signal.emit(80, "Calculating unique items...")
        unique_in_a = {val: map_a[val] for val in sorted(set_a - set_b)}
        unique_in_b = {val: map_b[val] for val in sorted(set_b - set_a)}

        self.progress_signal.emit(100, "Completed")
        self.finished_signal.emit(dup_a, dup_b, unique_in_a, unique_in_b, start)

    def analyze(self, orig, cmp):
        counter = Counter(cmp)
        duplicates = {}
        original_map = defaultdict(list)
        for o, c in zip(orig, cmp):
            if counter[c] > 1:
                original_map[c].append(o)
        for c_val, cnt in counter.items():
            if cnt > 1:
                duplicates[c_val] = (cnt, list(dict.fromkeys(original_map[c_val])))
        return set(cmp), duplicates

    def build_map(self, orig, cmp):
        original_map = defaultdict(list)
        for o, c in zip(orig, cmp):
            original_map[c].append(o)
        for k in original_map:
            original_map[k] = list(dict.fromkeys(original_map[k]))
        return original_map

class LargeTextComparatorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Large text comparator v0.5.2 by:xwk")
        self.setGeometry(100, 100, 1200, 800)
        self.bulk_operation = False
        self.initUI()

    def initUI(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        # Input area
        input_splitter = QSplitter()

        # List A section with file button
        a_widget = QWidget()
        a_layout = QVBoxLayout(a_widget)

        # List A file button and label
        a_file_layout = QHBoxLayout()
        self.load_a_btn = QPushButton("Load File...")
        self.load_a_btn.clicked.connect(lambda: self.load_file(0))
        self.a_label = QLabel("List A(0)")
        a_file_layout.addWidget(self.load_a_btn)
        a_file_layout.addStretch()  # 添加弹性空间，让标签靠右
        a_file_layout.addWidget(self.a_label)
        a_layout.addLayout(a_file_layout)

        self.text_a = QPlainTextEdit()
        self.text_a.setPlaceholderText("Paste text list A here, one per line or load from file")
        self.text_a.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.text_a.textChanged.connect(self.update_line_counts)
        a_layout.addWidget(self.text_a)

        # List B section with file button
        b_widget = QWidget()
        b_layout = QVBoxLayout(b_widget)

        # List B file button and label
        b_file_layout = QHBoxLayout()
        self.load_b_btn = QPushButton("Load File...")
        self.load_b_btn.clicked.connect(lambda: self.load_file(1))
        self.b_label = QLabel("List B(0)")
        b_file_layout.addWidget(self.load_b_btn)
        b_file_layout.addStretch()  # 添加弹性空间，让标签靠右
        b_file_layout.addWidget(self.b_label)
        b_layout.addLayout(b_file_layout)

        self.text_b = QPlainTextEdit()
        self.text_b.setPlaceholderText("Paste text list B here, one per line or load from file")
        self.text_b.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.text_b.textChanged.connect(self.update_line_counts)
        b_layout.addWidget(self.text_b)

        input_splitter.addWidget(a_widget)
        input_splitter.addWidget(b_widget)
        input_splitter.setSizes([600, 600])

        # Button area
        button_layout = QHBoxLayout()
        self.case_sensitive_checkbox = QCheckBox("Case sensitive")
        self.case_sensitive_checkbox.setChecked(False)

        self.compare_btn = QPushButton("Compare Text (Ctrl+R)")
        self.compare_btn.setShortcut("Ctrl+R")
        self.compare_btn.clicked.connect(self.compare_texts)

        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self.clear_all)

        button_layout.addWidget(self.case_sensitive_checkbox)
        button_layout.addWidget(self.compare_btn)
        button_layout.addWidget(self.clear_btn)

        # Result display
        self.tab_widget = QTabWidget()
        self.create_result_tabs()

        main_layout.addWidget(input_splitter)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.tab_widget)

        # Add progress bar, initially hidden
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        self.setCentralWidget(main_widget)

        # Add status bar
        self.statusBar().showMessage("Ready")

    def load_file(self, list_index):
        """加载文件到指定的文本框"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Select File for {'List A' if list_index == 0 else 'List B'}",
            "",
            "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
            except UnicodeDecodeError:
                try:
                    with open(file_path, 'r', encoding='gbk') as file:
                        content = file.read()
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to read file: {str(e)}")
                    return
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to read file: {str(e)}")
                return

            # 将文件内容加载到对应的文本框
            if list_index == 0:
                self.text_a.setPlainText(content)
            else:
                self.text_b.setPlainText(content)

            # 更新行数统计
            self.update_line_counts()

    def update_line_counts(self):
        if self.bulk_operation:
            return
        a_lines = len([line for line in self.text_a.toPlainText().split('\n') if line.strip()])
        b_lines = len([line for line in self.text_b.toPlainText().split('\n') if line.strip()])
        self.a_label.setText(f"List A({a_lines})")
        self.b_label.setText(f"List B({b_lines})")

    def create_result_tabs(self):
        self.dup_a_tab = QWidget()
        self.dup_b_tab = QWidget()
        self.unique_a_tab = QWidget()
        self.unique_b_tab = QWidget()
        self.tab_widget.addTab(self.dup_a_tab, "Duplicates in List A")
        self.tab_widget.addTab(self.dup_b_tab, "Duplicates in List B")
        self.tab_widget.addTab(self.unique_a_tab, "Unique in List A")
        self.tab_widget.addTab(self.unique_b_tab, "Unique in List B")

    def get_texts(self, text_edit):
        orig_lines = [line.strip() for line in text_edit.toPlainText().split('\n') if line.strip()]
        if self.case_sensitive_checkbox.isChecked():
            return orig_lines, orig_lines
        return orig_lines, [line.lower() for line in orig_lines]

    def compare_texts(self):
        orig_a, cmp_a = self.get_texts(self.text_a)
        orig_b, cmp_b = self.get_texts(self.text_b)

        if not cmp_a and not cmp_b:
            QMessageBox.information(self, "Message", "Please enter text to compare")
            return

        self.compare_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)

        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.statusBar().showMessage("Start comparing text...")

        self.compare_thread = CompareThread(orig_a, cmp_a, orig_b, cmp_b)
        self.compare_thread.progress_signal.connect(self.on_progress_update)
        self.compare_thread.finished_signal.connect(self.on_compare_finished)
        self.compare_thread.start()

    def on_progress_update(self, value, message):
        self.progress_bar.setValue(value)
        self.statusBar().showMessage(message)

    def on_compare_finished(self, dup_a, dup_b, unique_in_a, unique_in_b, start):
        self.update_result_tabs(dup_a, dup_b, unique_in_a, unique_in_b)

        elapsed = time.time() - start
        self.statusBar().showMessage(f"Comparison completed, took {elapsed:.2f} seconds")
        self.progress_bar.setVisible(False)
        self.compare_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)

    def update_result_tabs(self, dup_a, dup_b, unique_in_a, unique_in_b):
        self.update_table(self.dup_a_tab, dup_a, "Duplicate Count", "Original Text")
        self.update_table(self.dup_b_tab, dup_b, "Duplicate Count", "Original Text")
        self.update_unique_table(self.unique_a_tab, unique_in_a, "Original Text")
        self.update_unique_table(self.unique_b_tab, unique_in_b, "Original Text")

        self.tab_widget.setTabText(0, f"Duplicates in List A({len(dup_a)})")
        self.tab_widget.setTabText(1, f"Duplicates in List B({len(dup_b)})")
        self.tab_widget.setTabText(2, f"Unique in List A({len(unique_in_a)})")
        self.tab_widget.setTabText(3, f"Unique in List B({len(unique_in_b)})")

    def update_table(self, tab, data, header_count, header_orig):
        if tab.layout():
            QWidget().setLayout(tab.layout())

        layout = QVBoxLayout(tab)
        table = CopyableTableWidget()

        table.setColumnCount(2)
        table.setHorizontalHeaderLabels([header_count, header_orig])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)

        sorted_data = sorted(data.items(), key=lambda x: x[1][0], reverse=True)
        table.setRowCount(len(sorted_data))

        for i, (count_val, (count, orig_examples)) in enumerate(sorted_data):
            item_count = QTableWidgetItem(str(count))
            item_count.setFlags(item_count.flags() & ~Qt.ItemIsEditable)
            table.setItem(i, 0, item_count)

            item_text = QTableWidgetItem(", ".join(orig_examples))
            item_text.setFlags(item_text.flags() & ~Qt.ItemIsEditable)
            table.setItem(i, 1, item_text)

        layout.addWidget(table)

    def update_unique_table(self, tab, data, header_orig):
        if tab.layout():
            QWidget().setLayout(tab.layout())

        layout = QVBoxLayout(tab)
        table = CopyableTableWidget()

        table.setColumnCount(1)
        table.setHorizontalHeaderLabels([header_orig])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)

        sorted_data = sorted(data.items(), key=lambda x: x[0])
        table.setRowCount(len(sorted_data))

        for i, (key, orig_examples) in enumerate(sorted_data):
            item_text = QTableWidgetItem(", ".join(orig_examples))
            item_text.setFlags(item_text.flags() & ~Qt.ItemIsEditable)
            table.setItem(i, 0, item_text)

        layout.addWidget(table)

    def paste_large_text(self, text_edit, text):
        # You previous TextLoaderThread solution remains unchanged, skip here
        pass

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_V and event.modifiers() == Qt.ControlModifier:
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            if text and text.count('\n') > 1000:
                active_widget = self.focusWidget()
                if active_widget in (self.text_a, self.text_b):
                    self.paste_large_text(active_widget, text)
                    return
        super().keyPressEvent(event)

    def clear_all(self):
        self.text_a.clear()
        self.text_b.clear()
        for i in range(self.tab_widget.count()):
            self.tab_widget.removeTab(0)
        self.create_result_tabs()
        self.statusBar().showMessage("All content cleared")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(app.font())
    window = LargeTextComparatorApp()
    window.show()
    sys.exit(app.exec_())
