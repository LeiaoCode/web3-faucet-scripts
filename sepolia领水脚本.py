import logging
import sys
import time
import threading
import requests
from queue import Queue
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QFileDialog, QSpinBox,
    QMessageBox, QProgressBar, QGroupBox, QGraphicsDropShadowEffect, QTextEdit,
    QSplitter, QTextBrowser, QComboBox, QFormLayout
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QSettings
from PyQt5.QtGui import QFont, QColor, QIcon, QLinearGradient, QBrush
import openpyxl
from pynocaptcha import ReCaptchaUniversalCracker
import json
import os

# Configuration
ALCHEMY_FAUCET_URL = "https://www.alchemy.com/faucets/ethereum-sepolia"  # This is a placeholder; actual interaction may require form POST
RECAPTCHA_SITE_KEY = "6LfA4dgpAAAAAL3otS0QoaS5mEIIr6F4ZlkT3L5N"  # Replace with actual site key from the faucet page
TWOCAPTCHA_API_KEY = "YOUR_2CAPTCHA_API_KEY"  # Replace with your 2Captcha API key
SUCCESS_LOG_FILE = "success_log.json"  # File to store success timestamps

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

class FaucetWorker(threading.Thread):
    def __init__(self, queue, proxy, wallet_address, signal, log_signal, nocaptcha_token):
        super().__init__()
        self.queue = queue
        self.proxy = proxy
        self.wallet_address = wallet_address
        self.signal = signal
        self.log_signal = log_signal
        self.nocaptcha_token = nocaptcha_token

    def run(self):
        try:
            # Solve reCAPTCHA
            cracker = ReCaptchaUniversalCracker(
                user_token=self.nocaptcha_token,
                sitekey="6Le6xNgUAAAAAHDXXUgcrCYACaq_K-iUTa-BIm4h",
                referer="https://visa-fr.tlscontact.com/gb/lon/login.php",
                size="invisible",
                action="login_form",
                title="Login",
                debug=True,
            )
            ret = cracker.crack()
            print(ret)
            token = ret

            # Prepare proxies
            proxies = {
                'http': self.proxy,
                'https': self.proxy,
            } if self.proxy else None

            # Simulate faucet request (this is a placeholder; adjust based on actual API/form)
            # Actual faucet might require POST to a specific endpoint with wallet and token
            response = requests.post(
                ALCHEMY_FAUCET_URL,  # Replace with actual POST URL if different
                data={
                    'address': self.wallet_address,
                    'g-recaptcha-response': token['code']
                },
                proxies=proxies,
                timeout=30
            )

            if response.status_code == 200 and 'success' in response.text.lower():
                success = True
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                success = False
                timestamp = None
        except Exception as e:
            success = False
            timestamp = None
            self.log_signal.emit(f"错误: {self.wallet_address} - {e}")

        self.signal.emit(self.wallet_address, success, timestamp)
        self.queue.task_done()

class UpdateSignal(QObject):
    updated = pyqtSignal(str, bool, str)
    log_updated = pyqtSignal(str)

class FaucetUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Web3 水龙头专业版")
        self.setWindowIcon(QIcon("icon.png"))  # Assume an icon file for tech logo
        self.resize(1200, 800)  # Larger default size for better visibility and layout

        # Define the config file path (use the software's directory)
        self.config_path = os.path.join(os.getcwd(), 'config.ini')
        self.settings = QSettings(self.config_path, QSettings.IniFormat)  # INI format

        # Main layout: Use QSplitter for left-right structure
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Left side: Configuration and Controls
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(15)
        left_widget.setLayout(left_layout)

        # Title label for branding
        title_label = QLabel("Web3 水龙头控制中心")
        title_label.setFont(QFont("Microsoft YaHei", 20, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(title_label)

        # Input group
        input_group = QGroupBox("配置")
        input_layout = QFormLayout()
        input_layout.setLabelAlignment(Qt.AlignRight)
        input_layout.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        input_layout.setContentsMargins(10, 10, 10, 10)
        input_layout.setSpacing(10)
        input_group.setLayout(input_layout)

        # Proxy type
        self.proxy_type_label = QLabel("代理类型:")
        self.proxy_type_combo = QComboBox()
        self.proxy_type_combo.addItems(["HTTP", "SOCKS5"])
        self.proxy_type_combo.currentTextChanged.connect(self.save_settings)
        input_layout.addRow(self.proxy_type_label, self.proxy_type_combo)

        # Proxy username
        self.proxy_username_label = QLabel("用户名:")
        self.proxy_username_input = QLineEdit()
        self.proxy_username_input.textChanged.connect(self.save_settings)
        input_layout.addRow(self.proxy_username_label, self.proxy_username_input)

        # Proxy password
        self.proxy_password_label = QLabel("密码:")
        self.proxy_password_input = QLineEdit()
        self.proxy_password_input.setEchoMode(QLineEdit.Password)
        self.proxy_password_input.textChanged.connect(self.save_settings)
        input_layout.addRow(self.proxy_password_label, self.proxy_password_input)

        # Proxy IP
        self.proxy_ip_label = QLabel("IP:")
        self.proxy_ip_input = QLineEdit()
        self.proxy_ip_input.textChanged.connect(self.save_settings)
        input_layout.addRow(self.proxy_ip_label, self.proxy_ip_input)

        # Proxy port
        self.proxy_port_label = QLabel("端口:")
        self.proxy_port_spin = QSpinBox()
        self.proxy_port_spin.setMinimum(1)
        self.proxy_port_spin.setMaximum(65535)
        self.proxy_port_spin.valueChanged.connect(self.save_settings)
        input_layout.addRow(self.proxy_port_label, self.proxy_port_spin)

        # NoCaptcha token
        self.nocaptcha_label = QLabel("NoCaptcha 密钥:")
        self.nocaptcha_input = QLineEdit()
        self.nocaptcha_input.setEchoMode(QLineEdit.Password)
        self.nocaptcha_input.textChanged.connect(self.save_settings)
        input_layout.addRow(self.nocaptcha_label, self.nocaptcha_input)

        # Thread count
        self.thread_label = QLabel("并发线程数:")
        self.thread_spin = QSpinBox()
        self.thread_spin.setMinimum(1)
        self.thread_spin.setMaximum(20)
        self.thread_spin.setValue(1)
        self.thread_spin.valueChanged.connect(self.save_settings)
        input_layout.addRow(self.thread_label, self.thread_spin)

        left_layout.addWidget(input_group)

        # Load saved settings after all widgets are created
        self.load_settings()

        # Import button
        self.import_btn = QPushButton("导入钱包地址")
        self.import_btn.clicked.connect(self.import_wallets)
        left_layout.addWidget(self.import_btn)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setFormat("%p% 完成")
        left_layout.addWidget(self.progress)

        # Buttons group
        btn_group = QGroupBox("控制")
        btn_layout = QHBoxLayout()
        btn_group.setLayout(btn_layout)

        self.start_btn = QPushButton("开始")
        self.start_btn.clicked.connect(self.start_faucet)
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.clicked.connect(self.pause_faucet)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.pause_btn)

        left_layout.addWidget(btn_group)

        # Software info at bottom left
        info_browser = QTextBrowser()
        info_browser.setHtml("""
            <h3>软件说明</h3>
            <p><b>作者:</b> Grok AI</p>
            <p><b>版本:</b> 1.0</p>
            <p><b>操作流程:</b></p>
            <ol>
                <li>导入钱包地址（支持 .txt 或 .xlsx 文件）。</li>
                <li>可选：输入代理 IP 和端口。</li>
                <li>设置并发线程数。</li>
                <li>点击“开始”启动 faucet 请求。</li>
                <li>监控表格和日志以查看进度和结果。</li>
            </ol>
            <p>注意：请确保 CAPTCHA 服务和代理有效，以避免请求失败。</p>
        """)
        info_browser.setReadOnly(True)
        info_browser.setOpenExternalLinks(True)
        left_layout.addWidget(info_browser)
        left_layout.addStretch()  # Push content to top, but info at bottom

        splitter.addWidget(left_widget)

        # Right side: Table and Log
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(15)
        right_widget.setLayout(right_layout)

        # Table for wallets (remove Index column)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["钱包地址", "成功", "时间戳"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 400)  # Wider wallet column (now column 0)
        self.table.verticalHeader().setDefaultSectionSize(30)  # Adjust row height for better visibility
        self.table.setMinimumHeight(300)  # Ensure enough height to show multiple rows
        right_layout.addWidget(self.table, stretch=2)

        # Log area
        log_group = QGroupBox("日志")
        log_layout = QVBoxLayout()
        log_group.setLayout(log_layout)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        right_layout.addWidget(log_group, stretch=1)

        splitter.addWidget(right_widget)

        # Set initial sizes for splitter (left 30%, right 70%)
        splitter.setSizes([int(self.width() * 0.3), int(self.width() * 0.7)])

        self.wallets = []
        self.queue = Queue()
        self.signal = UpdateSignal()
        self.signal.updated.connect(self.update_table)
        self.signal.log_updated.connect(self.update_log)
        self.running = False
        self.paused = False
        self.proxy_list = []
        self.success_log = self.load_success_log()  # Load success log

        # Apply styles
        self.apply_styles()

        # Add shadows for depth
        self.add_shadows()

    def load_settings(self):
        """加载之前保存的配置"""
        # 提取配置项值到临时变量
        proxy_password = self.settings.value("proxy_password", "")
        proxy_ip = self.settings.value("proxy_ip", "")
        proxy_type = self.settings.value("proxy_type", "HTTP")
        proxy_username = self.settings.value("proxy_username", "")
        proxy_port = int(self.settings.value("proxy_port", 0))
        nocaptcha_token = self.settings.value("nocaptcha_token", "")
        thread_count = int(self.settings.value("thread_count", 1))

        # 设置界面控件的值
        self.proxy_type_combo.setCurrentText(proxy_type)
        self.proxy_username_input.setText(proxy_username)
        self.proxy_password_input.setText(proxy_password)
        self.proxy_ip_input.setText(proxy_ip)
        self.proxy_port_spin.setValue(proxy_port)
        self.nocaptcha_input.setText(nocaptcha_token)
        self.thread_spin.setValue(thread_count)

    def save_settings(self):
        self.settings.setValue("proxy_type", self.proxy_type_combo.currentText())
        self.settings.setValue("proxy_username", self.proxy_username_input.text())
        self.settings.setValue("proxy_password", self.proxy_password_input.text())
        self.settings.setValue("proxy_ip", self.proxy_ip_input.text())
        self.settings.setValue("proxy_port", self.proxy_port_spin.value())
        self.settings.setValue("nocaptcha_token", self.nocaptcha_input.text())
        self.settings.setValue("thread_count", self.thread_spin.value())
        self.settings.sync()  # Ensure settings are saved immediately

    def load_success_log(self):
        if os.path.exists(SUCCESS_LOG_FILE):
            with open(SUCCESS_LOG_FILE, 'r') as f:
                return json.load(f)
        return {}

    def save_success_log(self):
        with open(SUCCESS_LOG_FILE, 'w') as f:
            json.dump(self.success_log, f)

    def apply_styles(self):
        # Enhanced QSS stylesheet for better look
        self.setStyleSheet("""
            QWidget {
                background-color: #1A1A1A;
                color: #E0E0E0;
                font-family: 'Microsoft YaHei';
                font-size: 13pt;
            }
            QSplitter::handle {
                background: #00BFFF;
                width: 5px;
            }
            QGroupBox {
                border: 1px solid #00BFFF;
                border-radius: 10px;
                margin-top: 12px;
                padding: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                color: #00BFFF;
                padding: 0 5px;
            }
            QLabel {
                color: #A0A0A0;
            }
            QLineEdit, QSpinBox, QComboBox {
                background-color: #282828;
                border: 1px solid #0080FF;
                border-radius: 6px;
                padding: 6px;
                color: #E0E0E0;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                border: 1px solid #00FFFF;
                box-shadow: 0 0 8px #00FFFF;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0080FF, stop:1 #00FFFF);
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                color: #FFFFFF;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00FFFF, stop:1 #0080FF);
                box-shadow: 0 0 12px #00FFFF;
            }
            QPushButton:pressed {
                background: #0060FF;
            }
            QTableWidget {
                background-color: #282828;
                alternate-background-color: #202020;
                gridline-color: #0080FF;
                border: 1px solid #0080FF;
                border-radius: 6px;
            }
            QTableWidget::item {
                color: #E0E0E0;
            }
            QTableWidget::item:selected {
                background-color: #0080FF;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0080FF, stop:1 #00FFFF);
                color: #FFFFFF;
                padding: 6px;
                border: none;
            }
            QProgressBar {
                background-color: #282828;
                border: 1px solid #0080FF;
                border-radius: 6px;
                text-align: center;
                color: #FFFFFF;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0080FF, stop:1 #00FFFF);
                border-radius: 6px;
            }
            QTextEdit, QTextBrowser {
                background-color: #282828;
                border: 1px solid #0080FF;
                border-radius: 6px;
                color: #E0E0E0;
            }
            QMessageBox {
                background-color: #1A1A1A;
                color: #E0E0E0;
            }
        """)

    def create_shadow(self):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 191, 255, 100))  # Softer cyan glow
        shadow.setOffset(0, 0)
        return shadow

    def add_shadows(self):
        # Add shadow effects to key widgets
        self.import_btn.setGraphicsEffect(self.create_shadow())
        self.start_btn.setGraphicsEffect(self.create_shadow())
        self.pause_btn.setGraphicsEffect(self.create_shadow())
        self.table.setGraphicsEffect(self.create_shadow())
        self.progress.setGraphicsEffect(self.create_shadow())
        self.log_text.setGraphicsEffect(self.create_shadow())

    def import_wallets(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "导入文件", "", "文本/Excel 文件 (*.txt *.xlsx)")
        if not file_path:
            return

        self.wallets = []
        self.table.setRowCount(0)

        if file_path.endswith('.txt'):
            with open(file_path, 'r') as f:
                self.wallets = [line.strip() for line in f if line.strip()]
        elif file_path.endswith('.xlsx'):
            wb = openpyxl.load_workbook(file_path)
            ws = wb.active
            for row in ws.iter_rows(min_row=2, values_only=True):
                if row[0]:  # Assuming first column is address
                    self.wallets.append(row[0])

        for wallet in self.wallets:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(wallet))
            self.table.setItem(row, 1, QTableWidgetItem("待处理"))
            self.table.setItem(row, 2, QTableWidgetItem(""))

        self.progress.setMaximum(len(self.wallets))


    def build_and_validate_proxy(self):
        """构建和验证代理"""
        # 获取用户输入
        proxy_type = self.proxy_type_combo.currentText().lower()  # 代理类型 (http 或 socks5)
        username = self.proxy_username_input.text().strip()  # 代理用户名
        password = self.proxy_password_input.text().strip()  # 代理密码
        host = self.proxy_ip_input.text().strip()  # 代理主机 (IP 或域名)
        port = self.proxy_port_spin.value()  # 代理端口

        logging.info(
            f"Proxy details: type={proxy_type}, username={username}, password={password}, host={host}, port={port}"
        )

        # 如果没有主机，直接返回 None (无代理模式)
        if not host:
            logging.info("未提供代理主机")
            return None

        # 验证端口范围
        if not (1 <= port <= 65535):
            logging.error(f"无效的端口: {port} (必须在1-65535之间)")
            return False

        # 初步验证主机: 如果是IP，使用正则检查IPv4；如果是域名，尝试DNS解析
        ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if re.match(ipv4_pattern, host):
            # 进一步检查每个 octet <= 255
            if any(int(octet) > 255 for octet in host.split('.')):
                logging.error(f"无效的IPv4地址: {host}")
                return False
        else:
            # 假设是域名，尝试解析
            try:
                socket.getaddrinfo(host, port)
            except socket.gaierror as e:
                logging.error(f"主机名解析失败: {host} - {e}")
                return False

        # 构建代理字符串
        auth = f"{username}:{password}@" if username and password else ""
        scheme = "http" if proxy_type == "http" else "socks5"  # 支持 http 或 socks5
        proxy_str = f"{scheme}://{auth}{host}:{port}"

        logging.info(f"构建的代理字符串: {proxy_str}")

        # 准备 proxies 字典 (支持 http 和 https)
        proxies = {
            "http": proxy_str,
            "https": proxy_str,
        }

        # 测试代理有效性，使用更可靠的测试URL
        test_url = "https://api.ipify.org?format=json"  # 返回当前IP的JSON
        try:
            response = requests.get(test_url, proxies=proxies, timeout=10)  # 增加超时到10秒
            if response.status_code == 200:
                try:
                    ip_data = response.json()
                    logging.info(f"代理有效: {proxy_str} - 通过代理的IP: {ip_data.get('ip')}")
                    return proxy_str
                except ValueError:
                    logging.error("代理响应不是有效的JSON")
                    return False
            else:
                logging.error(f"代理无效，响应状态码: {response.status_code}")
                return False
        except requests.exceptions.ProxyError as e:
            logging.error(f"代理连接错误: {e}")
            return False
        except requests.exceptions.Timeout as e:
            logging.error(f"代理测试超时: {e}")
            return False
        except requests.exceptions.RequestException as e:
            logging.error(f"代理测试失败: {e}")
            return False

    def start_faucet(self):
        if not self.wallets:
            QMessageBox.warning(self, "错误", "未导入钱包地址!")
            return

        proxy_str = self.build_and_validate_proxy()
        if proxy_str is False:
            QMessageBox.warning(self, "错误", "代理格式无效!")
            return

        nocaptcha_token = self.nocaptcha_input.text().strip()
        if not nocaptcha_token:
            QMessageBox.warning(self, "错误", "未输入NoCaptcha密钥!")
            return

        # Filter wallets that haven't succeeded in the last 72 hours
        now = datetime.now()
        filtered_wallets = []
        filtered_indices = []
        for idx, wallet in enumerate(self.wallets):
            last_success = self.success_log.get(wallet)
            if last_success:
                last_time = datetime.strptime(last_success, "%Y-%m-%d %H:%M:%S")
                if now - last_time < timedelta(hours=72):
                    self.update_log(f"跳过 {wallet} - 上次成功时间: {last_success} (少于72小时)")
                    continue
            filtered_wallets.append(wallet)
            filtered_indices.append(idx)

        if not filtered_wallets:
            QMessageBox.information(self, "信息", "所有地址最近72小时内已成功，无需处理。")
            return

        # For dynamic proxies: here assuming one proxy per request; extend to rotate from list
        self.proxy_list = [proxy_str] * len(filtered_wallets) if proxy_str else [None] * len(filtered_wallets)
        self.filtered_indices = filtered_indices  # Store original indices for updating table

        self.running = True
        self.paused = False
        self.progress.setValue(0)
        self.progress.setMaximum(len(filtered_wallets))
        self.log_text.clear()

        thread_count = self.thread_spin.value()
        for i in range(len(filtered_wallets)):
            self.queue.put(i)

        for _ in range(thread_count):
            t = threading.Thread(target=self.worker_thread, args=(nocaptcha_token,))
            t.daemon = True
            t.start()

    def worker_thread(self, nocaptcha_token):
        while self.running and not self.queue.empty():
            if self.paused:
                time.sleep(1)
                continue
            idx = self.queue.get()
            wallet = self.wallets[self.filtered_indices[idx]]
            proxy = self.proxy_list[idx]  # Rotate or use unique
            worker = FaucetWorker(self.queue, proxy, wallet, self.signal.updated, self.signal.log_updated, nocaptcha_token)
            worker.start()
            # Note: Since it's threaded, but to limit concurrency, we can use semaphore if needed

    def pause_faucet(self):
        self.paused = not self.paused
        self.pause_btn.setText("恢复" if self.paused else "暂停")

    def update_table(self, wallet, success, timestamp):
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == wallet:
                status_item = QTableWidgetItem("是" if success else "否")
                status_item.setForeground(QBrush(QColor(0, 255, 0) if success else QColor(255, 0, 0)))  # Green for yes, red for no
                self.table.setItem(row, 1, status_item)
                if timestamp:
                    self.table.setItem(row, 2, QTableWidgetItem(timestamp))
                if success:
                    self.success_log[wallet] = timestamp
                    self.save_success_log()
                break
        self.progress.setValue(self.progress.value() + 1)

        log_msg = f"{wallet} - 成功: {'是' if success else '否'} - 时间: {timestamp}"
        self.update_log(log_msg)

    def update_log(self, message):
        if message:
            self.log_text.append(message)
            self.log_text.ensureCursorVisible()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FaucetUI()
    window.show()
    sys.exit(app.exec_())