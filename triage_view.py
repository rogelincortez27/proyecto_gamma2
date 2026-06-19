"""
GAMMA — Vista de Triage
Cola automática: tabla izquierda con pacientes EN_ESPERA enviados por Recepción.
Clic en paciente → carga sus datos → registrar signos vitales → pasa al médico.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QFrame, QGridLayout, QMessageBox, QDoubleSpinBox,
    QSpinBox, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox
)
from PyQt6.QtCore import Qt, QTimer
from src.controllers.cola_controller import cola_controller, AreaDestino
from src.controllers.paciente_controller import paciente_controller
from src.controllers.paciente_controller import paciente_controller
from src.views._theme import NAVY, TEAL, SUCCESS, DANGER, WHITE, BORDER, TEXT, MUTED
from src.views._widgets import BannerWidget
from src.views._styles import btn_success, btn_secondary, btn_primary
from src.views._common import (
    INPUT_QSS, WIDGET_BG, TABLA_QSS,
    card_style, titulo_style, sec_style, campo_style
)


class TriageView(QWidget):
    def __init__(self):
        super().__init__()
        self._cola_sel = None   # Entrada de cola seleccionada
        self._visita_guardada_id = None
        self.setStyleSheet(WIDGET_BG)
        self._setup_ui()
        # Refresco automático cada 30 seg
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._cargar_cola)
        self._timer.start(30000)

    def _lbl(self, t):
        l = QLabel(t.upper()); l.setStyleSheet(campo_style()); return l

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 20, 32, 20)
        layout.setSpacing(12)

        enc = QHBoxLayout()
        enc.addWidget(QLabel("Triage — Signos Vitales", styleSheet=titulo_style()))
        enc.addStretch()
        layout.addLayout(enc)

        layout.addWidget(BannerWidget("🚑", "Triage — Cola de Atención", "", "#276749", "#48BB78"))

        # Splitter: cola izquierda | formulario derecha
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # ── PANEL IZQUIERDO: Cola de pacientes en espera ──────────────────────
        left = QFrame(); left.setStyleSheet(card_style())
        ll = QVBoxLayout(left); ll.setContentsMargins(16, 16, 16, 16); ll.setSpacing(10)

        lbl_cola = QLabel("PACIENTES EN ESPERA — TRIAGE")
        lbl_cola.setStyleSheet(
            f"font-size:11px;font-weight:700;color:{MUTED};letter-spacing:1px;"
            f"padding-bottom:8px;border-bottom:2px solid {TEAL};background:transparent;"
        )
        ll.addWidget(lbl_cola)

        nota = QLabel("🖱  Haga clic en un paciente para cargar sus datos")
        nota.setStyleSheet(f"color:{MUTED};font-size:11px;background:transparent;border:none;")
        ll.addWidget(nota)

        self.tabla_cola = QTableWidget(); self.tabla_cola.setColumnCount(3)
        self.tabla_cola.setHorizontalHeaderLabels(["#", "Paciente", "Hora"])
        self.tabla_cola.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabla_cola.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_cola.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_cola.verticalHeader().setVisible(False)
        self.tabla_cola.setShowGrid(False)
        self.tabla_cola.setAlternatingRowColors(True)
        self.tabla_cola.setStyleSheet(TABLA_QSS)
        self.tabla_cola.itemSelectionChanged.connect(self._seleccionar_paciente)
        ll.addWidget(self.tabla_cola)

        btn_ref = btn_secondary("↻  Actualizar Lista")
        btn_ref.clicked.connect(self._cargar_cola)
        ll.addWidget(btn_ref)
        splitter.addWidget(left)

        # ── PANEL DERECHO: Info paciente + Formulario signos vitales ──────────
        right = QFrame(); right.setStyleSheet(card_style())
        rl = QVBoxLayout(right); rl.setContentsMargins(20, 18, 20, 20); rl.setSpacing(14)

        # Info del paciente seleccionado
        lbl_sec = QLabel("PACIENTE SELECCIONADO")
        lbl_sec.setStyleSheet(
            f"font-size:11px;font-weight:700;color:{MUTED};letter-spacing:1px;"
            f"padding-bottom:8px;border-bottom:2px solid {TEAL};background:transparent;"
        )
        rl.addWidget(lbl_sec)

        self.lbl_pac = QLabel("Seleccione un paciente de la lista para comenzar.")
        self.lbl_pac.setWordWrap(True)
        self.lbl_pac.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_pac.setStyleSheet(
            f"color:{MUTED};font-size:13px;background:#F8FAFD;"
            f"border-radius:10px;padding:16px;border:1px solid {BORDER};"
        )
        self.lbl_pac.setMinimumHeight(60)
        rl.addWidget(self.lbl_pac)

        # Grid signos vitales
        lbl_sv = QLabel("SIGNOS VITALES")
        lbl_sv.setStyleSheet(
            f"font-size:11px;font-weight:700;color:{MUTED};letter-spacing:1px;"
            f"padding-bottom:8px;border-bottom:2px solid {TEAL};background:transparent;"
        )
        rl.addWidget(lbl_sv)

        gv = QGridLayout(); gv.setSpacing(12)
        for i in range(4): gv.setColumnStretch(i, 1)

        self.inp_pre = QLineEdit(); self.inp_pre.setPlaceholderText("120/80 mmHg"); self.inp_pre.setStyleSheet(INPUT_QSS)
        self.inp_tmp = QDoubleSpinBox(); self.inp_tmp.setRange(30,45); self.inp_tmp.setValue(36.5); self.inp_tmp.setSuffix(" °C"); self.inp_tmp.setStyleSheet(INPUT_QSS)
        self.inp_sat = QDoubleSpinBox(); self.inp_sat.setRange(50,100); self.inp_sat.setValue(98); self.inp_sat.setSuffix(" %"); self.inp_sat.setStyleSheet(INPUT_QSS)
        self.inp_fc  = QSpinBox(); self.inp_fc.setRange(30,250); self.inp_fc.setValue(72); self.inp_fc.setSuffix(" bpm"); self.inp_fc.setStyleSheet(INPUT_QSS)
        self.inp_fr  = QSpinBox(); self.inp_fr.setRange(5,60); self.inp_fr.setValue(16); self.inp_fr.setSuffix(" rpm"); self.inp_fr.setStyleSheet(INPUT_QSS)
        self.inp_pes = QDoubleSpinBox(); self.inp_pes.setRange(1,300); self.inp_pes.setValue(70); self.inp_pes.setSuffix(" kg"); self.inp_pes.setStyleSheet(INPUT_QSS)
        self.inp_tal = QDoubleSpinBox(); self.inp_tal.setRange(30,250); self.inp_tal.setValue(170); self.inp_tal.setSuffix(" cm"); self.inp_tal.setStyleSheet(INPUT_QSS)
        self.inp_glu = QLineEdit(); self.inp_glu.setPlaceholderText("mg/dL (opcional)"); self.inp_glu.setStyleSheet(INPUT_QSS)

        gv.addWidget(self._lbl("Presión Arterial"),   0,0); gv.addWidget(self.inp_pre, 1,0)
        gv.addWidget(self._lbl("Temperatura"),        0,1); gv.addWidget(self.inp_tmp, 1,1)
        gv.addWidget(self._lbl("Saturación O₂"),      0,2); gv.addWidget(self.inp_sat, 1,2)
        gv.addWidget(self._lbl("Frec. Cardíaca"),     0,3); gv.addWidget(self.inp_fc,  1,3)
        gv.addWidget(self._lbl("Frec. Respiratoria"), 2,0); gv.addWidget(self.inp_fr,  3,0)
        gv.addWidget(self._lbl("Peso"),               2,1); gv.addWidget(self.inp_pes, 3,1)
        gv.addWidget(self._lbl("Talla"),              2,2); gv.addWidget(self.inp_tal, 3,2)
        gv.addWidget(self._lbl("Glucemia"),           2,3); gv.addWidget(self.inp_glu, 3,3)
        rl.addLayout(gv)

        # Destino
        dest_row = QHBoxLayout(); dest_row.setSpacing(12)
        lbl_dest = QLabel("ENVIAR A:"); lbl_dest.setStyleSheet(campo_style())
        self.cmb_destino = QComboBox(); self.cmb_destino.setStyleSheet(INPUT_QSS)
        self.cmb_destino.addItem("🩺  Medicina General",  AreaDestino.MEDICINA_GENERAL)
        self.cmb_destino.addItem("🫀  Medicina Interna",  AreaDestino.MEDICINA_INTERNA)
        dest_row.addWidget(lbl_dest); dest_row.addWidget(self.cmb_destino); dest_row.addStretch()
        rl.addLayout(dest_row)

        # Botones: Guardar signos | Enviar al Médico
        br = QHBoxLayout(); br.setSpacing(12); br.addStretch()
        self.btn_g = btn_success("💾  Guardar Signos Vitales")
        self.btn_g.setEnabled(False)
        self.btn_g.clicked.connect(self._guardar)

        self.btn_enviar = btn_primary("🩺  Enviar al Médico")
        self.btn_enviar.setEnabled(False)
        self.btn_enviar.clicked.connect(self._enviar_medico)
        br.addWidget(self.btn_g); br.addWidget(self.btn_enviar)
        rl.addLayout(br)

        splitter.addWidget(right)
        splitter.setSizes([320, 680])
        layout.addWidget(splitter, stretch=1)

        self._cargar_cola()

    # ── Lógica ────────────────────────────────────────────────────────────────

    def _cargar_cola(self):
        registros = cola_controller.obtener_cola_por_area(AreaDestino.TRIAGE)
        self.tabla_cola.setRowCount(0)
        self.tabla_cola.setRowCount(len(registros))
        for i, r in enumerate(registros):
            self.tabla_cola.setItem(i, 0, QTableWidgetItem(str(r.id)))
            nombre = r.paciente.nombre_completo if r.paciente else f"#{r.paciente_id}"
            self.tabla_cola.setItem(i, 1, QTableWidgetItem(nombre))
            self.tabla_cola.setItem(i, 2, QTableWidgetItem(r.fecha_hora.strftime("%H:%M")))
            self.tabla_cola.item(i, 0).setData(Qt.ItemDataRole.UserRole, r)
        if not registros:
            self.lbl_pac.setText("No hay pacientes en espera en este momento.")

    def _seleccionar_paciente(self):
        if not self.tabla_cola.selectedItems(): return
        r = self.tabla_cola.item(self.tabla_cola.currentRow(), 0).data(Qt.ItemDataRole.UserRole)
        if not r: return
        self._cola_sel = r
        pac = r.paciente
        self.lbl_pac.setText(
            f"👤  {pac.nombre_completo}  |  "
            f"Cédula: {pac.cedula}  |  "
            f"Edad: {pac.edad} años\n"
            f"En espera desde: {r.fecha_hora.strftime('%H:%M')}"
        )
        self.lbl_pac.setStyleSheet(
            f"color:{SUCCESS};font-size:13px;font-weight:600;"
            f"background:#F0FFF4;border-radius:10px;"
            f"padding:16px;border:1px solid #9AE6B4;"
        )
        self.btn_g.setEnabled(True)

    def _guardar(self):
        """Guarda los signos vitales en la BD y habilita el botón Enviar al Médico."""
        if not self._cola_sel:
            QMessageBox.warning(self, "Atención", "Seleccione un paciente de la cola."); return

        pac   = self._cola_sel.paciente
        datos = {
            "motivo_consulta":     f"Triage — {pac.nombre_completo}",
            "presion_arterial":    self.inp_pre.text() or None,
            "temperatura":         self.inp_tmp.value(),
            "saturacion_oxigeno":  self.inp_sat.value(),
            "frecuencia_cardiaca": self.inp_fc.value(),
            "peso_kg":             self.inp_pes.value(),
            "talla_cm":            self.inp_tal.value(),
            "observaciones": (
                f"FR: {self.inp_fr.value()} rpm"
                + (f" | Glucemia: {self.inp_glu.text()} mg/dL" if self.inp_glu.text().strip() else "")
            ),
        }

        # Guardar visita en BD (solo signos vitales, sin mover la cola todavía)
        self.btn_g.setEnabled(False)
        ok, msg, v = paciente_controller.registrar_visita(pac.id, datos)
        self.btn_g.setEnabled(True)

        if ok:
            self._visita_guardada_id = v.id
            # Bloquear campos (ya se guardaron)
            for inp in [self.inp_pre, self.inp_glu]:
                inp.setReadOnly(True)
            for sp in [self.inp_tmp, self.inp_sat, self.inp_fc, self.inp_fr, self.inp_pes, self.inp_tal]:
                sp.setEnabled(False)
            self.btn_g.setEnabled(False)
            # Habilitar botón enviar
            self.btn_enviar.setEnabled(True)
            QMessageBox.information(self, "Signos Guardados", "Signos vitales guardados. Presione Enviar al Medico.")
        else:
            QMessageBox.warning(self, "⚠ Error", msg)

    def _enviar_medico(self):
        """Mueve al paciente de la cola de Triage a la cola del Médico."""
        if not self._cola_sel:
            QMessageBox.warning(self, "Atención", "Sin paciente seleccionado."); return

        area = self.cmb_destino.currentData()
        self.btn_enviar.setEnabled(False)
        ok, msg = cola_controller.pasar_a_medico(
            self._cola_sel.id, {}, area
        )
        self.btn_enviar.setEnabled(True)

        if ok:
            QMessageBox.information(self, "✅ Enviado", msg)
            self._limpiar()
            self._cargar_cola()
        else:
            QMessageBox.warning(self, "⚠ Error", msg)

    def _limpiar(self):
        self.inp_pre.setReadOnly(False)
        self.inp_pre.clear()
        self.inp_glu.setReadOnly(False)
        self.inp_glu.clear()
        self.inp_tmp.setValue(36.5); self.inp_sat.setValue(98)
        self.inp_fc.setValue(72); self.inp_fr.setValue(16)
        self.inp_pes.setValue(70); self.inp_tal.setValue(170)
        self._cola_sel = None
        self._visita_guardada_id = None
        self.btn_g.setEnabled(False)
        self.lbl_pac.setText("Seleccione un paciente de la lista para comenzar.")
        self.lbl_pac.setStyleSheet(
            f"color:{MUTED};font-size:13px;background:#F8FAFD;"
            f"border-radius:10px;padding:16px;border:1px solid {BORDER};"
        )
        self.tabla_cola.clearSelection()
