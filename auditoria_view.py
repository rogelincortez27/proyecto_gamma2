"""
GAMMA — Vista de Auditoría del Sistema
Solo para ADMIN. Lee logs_auditoria de forma pasiva.
ISO 27001 — Trazabilidad completa del sistema.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit
)
from PyQt6.QtCore import Qt
from src.models.models import AuditoriaLog, Usuario
from src.models.database import db_manager
from src.views._theme import NAVY, TEAL, WHITE, BORDER, MUTED, TEXT
from src.views._widgets import BannerWidget
from src.views._styles import btn_secondary, btn_buscar
from src.views._common import (
    TABLA_QSS, INPUT_QSS, WIDGET_BG,
    card_style, titulo_style, sec_style
)


class AuditoriaView(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(WIDGET_BG)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 20, 32, 20)
        layout.setSpacing(12)

        # Encabezado
        enc = QHBoxLayout()
        enc.addWidget(QLabel("Auditoría del Sistema", styleSheet=titulo_style()))
        enc.addStretch()
        btn_ref = btn_secondary("↻  Actualizar")
        btn_ref.clicked.connect(self._cargar)
        enc.addWidget(btn_ref)
        layout.addLayout(enc)

        layout.addWidget(BannerWidget(
            "🔍", "Auditoría del Sistema — Logs de Acceso", "", NAVY, "#1A4F8A"
        ))

        # Card con tabla
        card = QFrame(); card.setStyleSheet(card_style())
        cl = QVBoxLayout(card); cl.setContentsMargins(20, 16, 20, 16); cl.setSpacing(12)

        # Filtro
        lbl_sec = QLabel("REGISTRO DE ACTIVIDAD DEL SISTEMA")
        lbl_sec.setStyleSheet(sec_style())
        cl.addWidget(lbl_sec)

        busq_row = QHBoxLayout(); busq_row.setSpacing(10)
        self.inp_filtro = QLineEdit()
        self.inp_filtro.setPlaceholderText("Filtrar por usuario o acción...")
        self.inp_filtro.setStyleSheet(INPUT_QSS)
        self.inp_filtro.textChanged.connect(self._filtrar)
        btn_b = btn_buscar("Filtrar"); btn_b.clicked.connect(self._filtrar)
        busq_row.addWidget(self.inp_filtro); busq_row.addWidget(btn_b)
        cl.addLayout(busq_row)

        # Tabla — solo lectura
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(5)
        self.tabla.setHorizontalHeaderLabels([
            "ID", "Usuario", "Acción", "Tabla Afectada", "Fecha y Hora"
        ])
        self.tabla.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setShowGrid(False)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setStyleSheet(TABLA_QSS)
        cl.addWidget(self.tabla)

        # Contador
        self.lbl_total = QLabel("")
        self.lbl_total.setStyleSheet(
            f"color:{MUTED};font-size:11px;background:transparent;border:none;"
        )
        cl.addWidget(self.lbl_total)

        layout.addWidget(card, stretch=1)
        self._cargar()

    def _cargar(self):
        """SELECT de auditoria_logs con JOIN a usuarios. Solo lectura."""
        session = db_manager.get_session()
        try:
            logs = (
                session.query(AuditoriaLog, Usuario)
                .outerjoin(Usuario, AuditoriaLog.usuario_id == Usuario.id)
                .order_by(AuditoriaLog.timestamp.desc())
                .limit(500)
                .all()
            )
            self._logs = logs
            self._poblar(logs)
        finally:
            session.close()

    def _poblar(self, logs):
        self.tabla.setRowCount(0)
        self.tabla.setRowCount(len(logs))
        for i, (log, usr) in enumerate(logs):
            self.tabla.setItem(i, 0, QTableWidgetItem(str(log.id)))
            self.tabla.setItem(i, 1, QTableWidgetItem(
                usr.nombre_usuario if usr else f"ID {log.usuario_id}"))
            self.tabla.setItem(i, 2, QTableWidgetItem(log.accion))
            self.tabla.setItem(i, 3, QTableWidgetItem(log.tabla_afectada or "—"))
            self.tabla.setItem(i, 4, QTableWidgetItem(
                log.timestamp.strftime("%d/%m/%Y %H:%M:%S")))
        self.lbl_total.setText(f"Mostrando {len(logs)} registros (máximo 500 más recientes)")

    def _filtrar(self):
        t = self.inp_filtro.text().strip().lower()
        if not t:
            self._poblar(self._logs); return
        filtrados = [
            (log, usr) for log, usr in self._logs
            if t in (usr.nombre_usuario if usr else "").lower()
            or t in log.accion.lower()
            or t in (log.tabla_afectada or "").lower()
        ]
        self._poblar(filtrados)
