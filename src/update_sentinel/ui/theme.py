"""Identidade visual Qt com paletas claras e escuras, sem dependências extras."""

from PySide6.QtGui import QColor, QPalette


def palette(dark: bool) -> QPalette:
    colors = QPalette()
    roles = {
        QPalette.ColorRole.Window: "#101722" if dark else "#f3f6fa",
        QPalette.ColorRole.WindowText: "#edf2fa" if dark else "#17253c",
        QPalette.ColorRole.Base: "#182231" if dark else "#ffffff",
        QPalette.ColorRole.AlternateBase: "#202e40" if dark else "#edf3fb",
        QPalette.ColorRole.Text: "#edf2fa" if dark else "#17253c",
        QPalette.ColorRole.Button: "#182231" if dark else "#ffffff",
        QPalette.ColorRole.ButtonText: "#edf2fa" if dark else "#17253c",
        QPalette.ColorRole.Highlight: "#377deb",
        QPalette.ColorRole.HighlightedText: "#ffffff",
        QPalette.ColorRole.ToolTipBase: "#182231" if dark else "#ffffff",
        QPalette.ColorRole.ToolTipText: "#edf2fa" if dark else "#17253c",
    }
    for role, value in roles.items():
        colors.setColor(role, QColor(value))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText):
        colors.setColor(QPalette.ColorGroup.Disabled, role, QColor("#7d8b9e"))
    return colors


def stylesheet(dark: bool) -> str:
    surface = "#182231" if dark else "#ffffff"
    background = "#101722" if dark else "#f3f6fa"
    border = "#2a384b" if dark else "#dfe6f0"
    muted = "#a6b5ca" if dark else "#60718a"
    hover = "#24344a" if dark else "#edf3fc"
    text = "#edf2fa" if dark else "#17253c"
    return f"""
        QMainWindow, QWidget#workspace {{ background: {background}; }}
        QWidget {{ font-size: 13px; color: {text}; }}
        QFrame#sidebar {{ background: #101c30; border: none; }}
        QFrame#sidebar QLabel {{ color: #acbbd0; background: transparent; }}
        QFrame#sidebar QLabel#brand {{ color: #ffffff; font-size: 19px; font-weight: 700; }}
        QFrame#sidebar QLabel#brandMark {{ color: #6ea8ff; font-size: 28px; font-weight: 700; }}
        QFrame#sidebar QLabel#navCaption {{ color: #7e91af; font-size: 11px; font-weight: 600; }}
        QFrame#sidebar QPushButton {{
            text-align: left; background: transparent; border: none; color: #acbbd0;
            padding: 11px 14px; border-radius: 7px;
        }}
        QFrame#sidebar QPushButton:hover {{ background: #1a2c47; color: white; }}
        QFrame#sidebar QPushButton:checked {{ background: #233e63; color: #ffffff; }}
        QFrame#sidebar QPushButton:disabled {{ color: #62738d; }}
        QFrame#topbar {{ background: {surface}; border-bottom: 1px solid {border}; }}
        QLabel#breadcrumb {{ font-weight: 600; }}
        QLabel#muted, QLabel#statusLine {{ color: {muted}; }}
        QLabel#eyebrow {{ color: #548ae0; font-size: 11px; font-weight: 700; }}
        QLabel#heroTitle {{ font-size: 27px; font-weight: 700; }}
        QLabel#sectionTitle {{ font-size: 16px; font-weight: 600; }}
        QLabel#metricValue {{ font-size: 26px; font-weight: 700; }}
        QLabel#stateBadge {{
            background: {hover}; color: {muted}; border: 1px solid {border};
            border-radius: 12px; padding: 5px 12px; font-size: 11px; font-weight: 600;
        }}
        QLabel#stateBadge[state="busy"] {{ background: #1e3c66; color: #d4e6ff; }}
        QLabel#stateBadge[state="attention"] {{ background: #553e1c; color: #ffe0a1; }}
        QFrame#heroCard, QFrame#guidanceCard, QFrame#metricCard, QFrame#activityCard {{
            background: {surface}; border: 1px solid {border}; border-radius: 12px;
        }}
        QFrame#guidanceCard[role="attention"] {{ border-left: 3px solid #d49a35; }}
        QFrame#guidanceCard[role="next"] {{ border-left: 3px solid #377deb; }}
        QLabel#stepState {{ color: {muted}; font-size: 12px; }}
        QLabel#stepState[state="active"] {{ color: #548ae0; font-weight: 700; }}
        QLabel#stepState[state="done"] {{ color: {"#75ceb0" if dark else "#24735c"}; }}
        QLabel#stepState[state="error"] {{ color: {"#ffc97b" if dark else "#945e12"}; }}
        QPushButton {{
            background: {surface}; border: 1px solid {border}; border-radius: 7px;
            padding: 9px 14px; font-weight: 500;
        }}
        QPushButton:hover {{ background: {hover}; border-color: #779ad0; }}
        QPushButton:pressed {{ background: {hover}; }}
        QPushButton:disabled {{ color: {muted}; background: {background}; }}
        QPushButton#primary {{ background: #2869d5; color: white; border: 1px solid #2869d5; }}
        QPushButton#primary:hover {{ background: #347bec; }}
        QPushButton#primary:pressed {{ background: #2159b5; }}
        QPushButton#primary:disabled {{ background: #335a91; color: #c3d4eb; }}
        QPushButton:focus, QLineEdit:focus, QComboBox:focus {{ border: 2px solid #548ae0; }}
        QTabWidget::pane {{ border: none; background: transparent; }}
        QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
        QTextEdit, QTableWidget, QLineEdit, QComboBox {{
            background: {surface}; color: {text}; border: 1px solid {border}; border-radius: 7px;
            selection-background-color: #2869d5; selection-color: white;
        }}
        QTextEdit {{ padding: 14px; }}
        QLineEdit, QComboBox {{ padding: 9px 12px; min-height: 18px; }}
        QHeaderView::section {{
            background: {hover}; color: {muted}; border: none;
            border-bottom: 1px solid {border}; padding: 12px 8px; font-weight: 600;
        }}
        QTableWidget {{ gridline-color: {border}; alternate-background-color: {hover}; }}
        QProgressBar {{ background: {hover}; border: none; border-radius: 3px; }}
        QProgressBar::chunk {{ background: #377deb; border-radius: 3px; }}
        QToolTip {{ color: {text}; background: {surface}; border: 1px solid {border}; }}
    """
