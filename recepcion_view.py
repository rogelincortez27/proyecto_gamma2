"""
GAMMA — Vista de Recepción
Flujo completo:
- Paciente NUEVO → Registrar → Enviar a Triage
- Paciente YA EXISTE → Buscar por cédula → Enviar a Triage
Sin módulo de citas. El médico indica verbalmente cuándo volver.
"""
from datetime import datetime, date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QDateEdit, QFrame, QSplitter, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QGridLayout,
    QStackedWidget, QPushButton
)
from PyQt6.QtCore import Qt, QTimer, QDate
from src.models.models import Gender
from src.controllers.paciente_controller import paciente_controller
from src.controllers.cola_controller import cola_controller, AreaDestino
from src.views._theme import NAVY, TEAL, WHITE, BORDER, TEXT, MUTED, SUCCESS, DANGER, AMBER
from src.views._widgets import BannerWidget
from src.views._styles import btn_primary, btn_secondary, btn_teal, btn_buscar
from src.views._common import (
    INPUT_QSS, WIDGET_BG, TABLA_QSS,
    card_style, titulo_style, sec_style, campo_style, setup_calendar_popup
)


class RecepcionView(QWidget):
    def __init__(self):
        super().__init__()
        self._pac_id = None
        self.setStyleSheet(WIDGET_BG)
        self._setup_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

    def _lbl(self, t):
        l = QLabel(t.upper())
        l.setStyleSheet(
            "color:#7A92A8;font-size:11px;font-weight:700;"
            "letter-spacing:0.5px;padding-top:4px;"
            "background:transparent;border:none;"
        )
        return l

    def _inp(self, ph):
        i = QLineEdit(); i.setPlaceholderText(ph)
        i.setStyleSheet(INPUT_QSS); i.setMinimumHeight(38)
        return i

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 20, 32, 20)
        layout.setSpacing(14)

        # Encabezado
        enc = QHBoxLayout()
        enc.addWidget(QLabel("Panel de Recepción", styleSheet=titulo_style()))
        enc.addStretch()
        self.lbl_hora = QLabel(datetime.now().strftime("%H:%M:%S"))
        self.lbl_hora.setStyleSheet(
            f"font-size:20px;font-weight:800;color:{NAVY};"
            "background:transparent;border:none;"
        )
        enc.addWidget(self.lbl_hora)
        layout.addLayout(enc)

        layout.addWidget(BannerWidget("🏥", "Recepción y Admisiones", "", NAVY, "#1A4F8A"))

        # Splitter principal
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # ── PANEL IZQUIERDO: Tabs Nuevo / Ya registrado ───────────────────────
        left_card = QFrame(); left_card.setStyleSheet(card_style())
        left_l = QVBoxLayout(left_card); left_l.setContentsMargins(20, 16, 20, 16); left_l.setSpacing(12)

        # Selector de modo
        modo_row = QHBoxLayout(); modo_row.setSpacing(0)
        self.btn_modo_nuevo = QPushButton("➕  Nuevo Paciente")
        self.btn_modo_existente = QPushButton("🔍  Ya Registrado")
        for btn in [self.btn_modo_nuevo, self.btn_modo_existente]:
            btn.setCheckable(True)
            btn.setFixedHeight(38)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background:#EDF2F7; color:{MUTED};
                    border:1px solid {BORDER}; font-size:13px;
                    font-weight:600; padding:0 20px;
                }}
                QPushButton:checked {{
                    background:{NAVY}; color:white;
                    border-color:{NAVY};
                }}
                QPushButton:hover:!checked {{ background:#E2E8F0; }}
            """)
        self.btn_modo_nuevo.setStyleSheet(
            self.btn_modo_nuevo.styleSheet() +
            "QPushButton { border-radius: 8px 0 0 8px; }"
        )
        self.btn_modo_existente.setStyleSheet(
            self.btn_modo_existente.styleSheet() +
            "QPushButton { border-radius: 0 8px 8px 0; }"
        )
        self.btn_modo_nuevo.setChecked(True)
        self.btn_modo_nuevo.clicked.connect(lambda: self._cambiar_modo(0))
        self.btn_modo_existente.clicked.connect(lambda: self._cambiar_modo(1))
        modo_row.addWidget(self.btn_modo_nuevo)
        modo_row.addWidget(self.btn_modo_existente)
        left_l.addLayout(modo_row)

        # Stack: 0 = Formulario nuevo, 1 = Búsqueda existente
        self.stack_modo = QStackedWidget()

        # ── PÁGINA 0: Formulario registro nuevo ──────────────────────────────
        pag_nuevo = QWidget()
        pn_l = QVBoxLayout(pag_nuevo); pn_l.setContentsMargins(0, 8, 0, 0); pn_l.setSpacing(0)

        sec_lbl = QLabel("DATOS DEL PACIENTE")
        sec_lbl.setStyleSheet(
            f"font-size:11px;font-weight:700;color:{MUTED};letter-spacing:1px;"
            f"padding-bottom:8px;border-bottom:2px solid {TEAL};background:transparent;"
        )
        pn_l.addWidget(sec_lbl)
        pn_l.addSpacing(12)

        g = QGridLayout()
        g.setHorizontalSpacing(14); g.setVerticalSpacing(8)
        g.setColumnStretch(0, 1); g.setColumnStretch(1, 1); g.setColumnStretch(2, 1)

        self.inp_ced = self._inp("Ej. 8-123-456")
        self.inp_nom = self._inp("Primer nombre")
        self.inp_ape = self._inp("Primer apellido")
        self.inp_fec = QDateEdit()
        self.inp_fec.setDisplayFormat("dd/MM/yyyy")
        self.inp_fec.setDate(QDate(1990, 1, 1))
        self.inp_fec.setCalendarPopup(True)
        self.inp_fec.setStyleSheet(INPUT_QSS); self.inp_fec.setMinimumHeight(38)
        setup_calendar_popup(self.inp_fec)
        self.cmb_gen = QComboBox(); self.cmb_gen.setStyleSheet(INPUT_QSS)
        self.cmb_gen.setMinimumHeight(38)
        for gn in Gender: self.cmb_gen.addItem(gn.value, gn)
        self.inp_nac = self._inp("Nacionalidad")
        self.inp_tel = self._inp("6000-0000")
        self.inp_dir = self._inp("Dirección completa")
        self.inp_ce  = self._inp("Nombre del contacto")
        self.inp_te  = self._inp("Teléfono de emergencia")

        g.addWidget(self._lbl("Cédula / ID *"), 0, 0)
        g.addWidget(self._lbl("Nombre *"),      0, 1)
        g.addWidget(self._lbl("Apellido *"),    0, 2)
        g.addWidget(self.inp_ced,               1, 0)
        g.addWidget(self.inp_nom,               1, 1)
        g.addWidget(self.inp_ape,               1, 2)
        g.setRowMinimumHeight(2, 10)
        g.addWidget(self._lbl("Fecha Nac. *"), 3, 0)
        g.addWidget(self._lbl("Género *"),     3, 1)
        g.addWidget(self._lbl("Nacionalidad"), 3, 2)
        g.addWidget(self.inp_fec,              4, 0)
        g.addWidget(self.cmb_gen,              4, 1)
        g.addWidget(self.inp_nac,              4, 2)
        g.setRowMinimumHeight(5, 10)
        g.addWidget(self._lbl("Teléfono"),            6, 0)
        g.addWidget(self._lbl("Dirección"),           6, 1)
        g.addWidget(self._lbl("Contacto Emergencia"), 6, 2)
        g.addWidget(self.inp_tel,                     7, 0)
        g.addWidget(self.inp_dir,                     7, 1)
        g.addWidget(self.inp_ce,                      7, 2)
        g.setRowMinimumHeight(8, 10)
        g.addWidget(self._lbl("Tel. Emergencia"), 9, 0)
        g.addWidget(self.inp_te,                 10, 0)
        pn_l.addLayout(g)
        pn_l.addSpacing(16)

        br_n = QHBoxLayout(); br_n.setSpacing(10); br_n.addStretch()
        btn_lim = btn_secondary("Limpiar"); btn_lim.clicked.connect(self._limpiar)
        self.btn_reg = btn_primary("✔  Registrar Paciente")
        self.btn_reg.clicked.connect(self._registrar)
        br_n.addWidget(btn_lim); br_n.addWidget(self.btn_reg)
        pn_l.addLayout(br_n)
        pn_l.addStretch()
        self.stack_modo.addWidget(pag_nuevo)

        # ── PÁGINA 1: Buscar paciente ya registrado ───────────────────────────
        pag_exist = QWidget()
        pe_l = QVBoxLayout(pag_exist); pe_l.setContentsMargins(0, 8, 0, 0); pe_l.setSpacing(12)

        nota = QLabel(
            "ℹ️  El paciente ya fue registrado anteriormente.\n"
            "Búscalo por cédula o nombre y envíalo directamente a Triage."
        )
        nota.setWordWrap(True)
        nota.setStyleSheet(
            f"color:#2C5282;font-size:12px;background:#EBF8FF;"
            f"border-radius:8px;padding:10px 14px;border-left:3px solid {TEAL};"
        )
        pe_l.addWidget(nota)

        busq_frame = QFrame()
        busq_frame.setStyleSheet(
            f"QFrame{{background:#F8FAFD;border-radius:10px;border:1px solid {BORDER};}}"
        )
        bf_l = QHBoxLayout(busq_frame); bf_l.setContentsMargins(12, 10, 12, 10); bf_l.setSpacing(10)
        self.inp_buscar_exist = QLineEdit()
        self.inp_buscar_exist.setPlaceholderText("Cédula o nombre del paciente...")
        self.inp_buscar_exist.setStyleSheet(INPUT_QSS)
        self.inp_buscar_exist.returnPressed.connect(self._buscar_existente)
        btn_be = btn_buscar("Buscar"); btn_be.clicked.connect(self._buscar_existente)
        bf_l.addWidget(self.inp_buscar_exist); bf_l.addWidget(btn_be)
        pe_l.addWidget(busq_frame)

        self.tabla_busqueda = QTableWidget(); self.tabla_busqueda.setColumnCount(3)
        self.tabla_busqueda.setHorizontalHeaderLabels(["ID", "Cédula", "Nombre"])
        self.tabla_busqueda.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tabla_busqueda.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_busqueda.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_busqueda.verticalHeader().setVisible(False)
        self.tabla_busqueda.setShowGrid(False)
        self.tabla_busqueda.setAlternatingRowColors(True)
        self.tabla_busqueda.setStyleSheet(TABLA_QSS)
        self.tabla_busqueda.itemSelectionChanged.connect(self._seleccionar_existente)
        pe_l.addWidget(self.tabla_busqueda)
        pe_l.addStretch()
        self.stack_modo.addWidget(pag_exist)

        left_l.addWidget(self.stack_modo)
        splitter.addWidget(left_card)

        # ── PANEL DERECHO: info + Enviar a Triage + Cola ─────────────────────
        right = QFrame(); right.setStyleSheet(card_style())
        rl = QVBoxLayout(right); rl.setContentsMargins(18, 18, 18, 18); rl.setSpacing(12)

        sec2 = QLabel("PACIENTE SELECCIONADO")
        sec2.setStyleSheet(
            f"font-size:11px;font-weight:700;color:{MUTED};letter-spacing:1px;"
            f"padding-bottom:8px;border-bottom:2px solid {TEAL};background:transparent;"
        )
        rl.addWidget(sec2)

        self.lbl_pac_info = QLabel("Registre o busque un paciente\npara habilitar el envío a Triage.")
        self.lbl_pac_info.setWordWrap(True)
        self.lbl_pac_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_pac_info.setStyleSheet(
            f"color:{MUTED};font-size:13px;background:#F8FAFD;"
            f"border-radius:10px;padding:20px;border:1px solid {BORDER};"
        )
        self.lbl_pac_info.setMinimumHeight(100)
        rl.addWidget(self.lbl_pac_info)

        self.btn_triage = btn_teal("🚑  Enviar a Triage")
        self.btn_triage.setEnabled(False)
        self.btn_triage.setFixedHeight(46)
        self.btn_triage.clicked.connect(self._enviar_triage)
        rl.addWidget(self.btn_triage)

        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{BORDER};border:none;")
        rl.addWidget(sep)

        sec3 = QLabel("COLA DE HOY — EN ESPERA (TRIAGE)")
        sec3.setStyleSheet(
            f"font-size:11px;font-weight:700;color:{MUTED};"
            "letter-spacing:1px;background:transparent;"
        )
        rl.addWidget(sec3)

        self.tabla_cola = QTableWidget(); self.tabla_cola.setColumnCount(3)
        self.tabla_cola.setHorizontalHeaderLabels(["#", "Paciente", "Hora"])
        self.tabla_cola.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabla_cola.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_cola.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_cola.verticalHeader().setVisible(False)
        self.tabla_cola.setShowGrid(False)
        self.tabla_cola.setAlternatingRowColors(True)
        self.tabla_cola.setStyleSheet(TABLA_QSS)
        self.tabla_cola.setMaximumHeight(200)
        rl.addWidget(self.tabla_cola)

        btn_ref = btn_secondary("↻  Actualizar Cola")
        btn_ref.clicked.connect(self._cargar_cola)
        rl.addWidget(btn_ref)
        rl.addStretch()

        splitter.addWidget(right)
        splitter.setSizes([600, 360])
        layout.addWidget(splitter, stretch=1)

        self._cargar_cola()

    # ── Lógica ────────────────────────────────────────────────────────────────

    def _tick(self):
        self.lbl_hora.setText(datetime.now().strftime("%H:%M:%S"))

    def _cambiar_modo(self, idx: int):
        self.stack_modo.setCurrentIndex(idx)
        self.btn_modo_nuevo.setChecked(idx == 0)
        self.btn_modo_existente.setChecked(idx == 1)
        # Resetear selección al cambiar modo
        self._pac_id = None
        self.btn_triage.setEnabled(False)
        self.lbl_pac_info.setText("Registre o busque un paciente\npara habilitar el envío a Triage.")
        self.lbl_pac_info.setStyleSheet(
            f"color:{MUTED};font-size:13px;background:#F8FAFD;"
            f"border-radius:10px;padding:20px;border:1px solid {BORDER};"
        )

    # MODO NUEVO: Registrar paciente
    def _registrar(self):
        fq = self.inp_fec.date()
        datos = {
            "cedula":              self.inp_ced.text().strip(),
            "nombre":              self.inp_nom.text().strip(),
            "apellido":            self.inp_ape.text().strip(),
            "fecha_nacimiento":    date(fq.year(), fq.month(), fq.day()),
            "genero":              self.cmb_gen.currentData(),
            "nacionalidad":        self.inp_nac.text().strip(),
            "telefono":            self.inp_tel.text().strip(),
            "direccion":           self.inp_dir.text().strip(),
            "contacto_emergencia": self.inp_ce.text().strip(),
            "telefono_emergencia": self.inp_te.text().strip(),
        }
        self.btn_reg.setEnabled(False)
        ok, msg, pac = paciente_controller.registrar_paciente(datos)
        self.btn_reg.setEnabled(True)

        if ok:
            self._set_pac_listo(pac.id, pac.nombre_completo, pac.cedula)
            self._limpiar()
        else:
            QMessageBox.warning(self, "⚠ Error", msg)

    # MODO EXISTENTE: Buscar paciente
    def _buscar_existente(self):
        t = self.inp_buscar_exist.text().strip()
        if not t: return
        res = paciente_controller.buscar_pacientes(t)
        self.tabla_busqueda.setRowCount(0)
        self.tabla_busqueda.setRowCount(len(res))
        for i, p in enumerate(res):
            self.tabla_busqueda.setItem(i, 0, QTableWidgetItem(str(p.id)))
            self.tabla_busqueda.setItem(i, 1, QTableWidgetItem(p.cedula))
            self.tabla_busqueda.setItem(i, 2, QTableWidgetItem(p.nombre_completo))
            self.tabla_busqueda.item(i, 0).setData(Qt.ItemDataRole.UserRole, p)
        if not res:
            QMessageBox.information(self, "Sin resultados", "No se encontró ningún paciente.")

    def _seleccionar_existente(self):
        if not self.tabla_busqueda.selectedItems(): return
        p = self.tabla_busqueda.item(
            self.tabla_busqueda.currentRow(), 0
        ).data(Qt.ItemDataRole.UserRole)
        if not p: return
        self._set_pac_listo(p.id, p.nombre_completo, p.cedula)

    def _set_pac_listo(self, pac_id: int, nombre: str, cedula: str):
        """Activa el panel derecho con la info del paciente listo para Triage."""
        self._pac_id = pac_id
        self.lbl_pac_info.setText(
            f"✅  {nombre}\n"
            f"Cédula: {cedula}  |  ID: #{pac_id}"
        )
        self.lbl_pac_info.setStyleSheet(
            f"color:{SUCCESS};font-size:13px;font-weight:600;"
            f"background:#F0FFF4;border-radius:10px;"
            f"padding:20px;border:1px solid #9AE6B4;"
        )
        self.btn_triage.setEnabled(True)

    # Enviar a Triage
    def _enviar_triage(self):
        if not self._pac_id:
            QMessageBox.warning(self, "Atención", "Seleccione un paciente primero.")
            return
        ok, msg = cola_controller.enviar_a_triage(self._pac_id)
        if ok:
            QMessageBox.information(self, "✅ Enviado", msg)
            self._pac_id = None
            self.btn_triage.setEnabled(False)
            self.lbl_pac_info.setText(
                "Registre o busque un paciente\npara habilitar el envío a Triage."
            )
            self.lbl_pac_info.setStyleSheet(
                f"color:{MUTED};font-size:13px;background:#F8FAFD;"
                f"border-radius:10px;padding:20px;border:1px solid {BORDER};"
            )
            self.tabla_busqueda.setRowCount(0)
            self.inp_buscar_exist.clear()
            self._cargar_cola()
        else:
            QMessageBox.warning(self, "⚠ Error", msg)

    def _cargar_cola(self):
        registros = cola_controller.obtener_cola_por_area(AreaDestino.TRIAGE)
        self.tabla_cola.setRowCount(0)
        self.tabla_cola.setRowCount(len(registros))
        for i, r in enumerate(registros):
            self.tabla_cola.setItem(i, 0, QTableWidgetItem(str(r.id)))
            nombre = r.paciente.nombre_completo if r.paciente else f"#{r.paciente_id}"
            self.tabla_cola.setItem(i, 1, QTableWidgetItem(nombre))
            self.tabla_cola.setItem(i, 2, QTableWidgetItem(r.fecha_hora.strftime("%H:%M")))

    def _limpiar(self):
        for w in self.findChildren(QLineEdit):
            if w != self.inp_buscar_exist:
                w.clear()
        self.cmb_gen.setCurrentIndex(0)
        self.inp_fec.setDate(QDate(1990, 1, 1))
        self.inp_ced.setFocus()
