"""
GAMMA — Vista de Consulta de Expedientes
Visualización estrictamente diferenciada por rol:

RECEPCION:
  - Contenedor A (Datos Personales): Visible + botón Editar Contacto
  - Contenedor B (Clínicos): OCULTO
  - Contenedor C (Historial): OCULTO

ENF_TRIAGE / ENF_ASISTENCIAL:
  - Contenedor A: Solo lectura
  - Contenedor B (Clínicos básicos): Visible + botón Actualizar
  - Contenedor C (Historial): Visible — al clic solo signos vitales, SIN diagnósticos

MEDICO / MEDICINA_INTERNA / ADMIN / DIRECTOR:
  - Contenedor A y B: Solo lectura
  - Contenedor C: Acceso total (signos vitales + evolución médica)
  - Sin botón "Ver Todos" (Ley 81)

ISO 27799 / Ley 81
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QStackedWidget, QScrollArea, QTextEdit, QTextBrowser,
    QSplitter, QMessageBox, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt
from src.controllers.paciente_controller import paciente_controller
from src.models.models import UserRole
from src.controllers.auth_controller import auth_controller
from src.views._theme import NAVY, TEAL, SUCCESS, DANGER, WHITE, BORDER, TEXT, MUTED, BG
from src.views._widgets import BannerWidget
from src.views._styles import btn_secondary, btn_buscar, btn_teal, btn_primary
from src.views._common import (
    TABLA_QSS, INPUT_QSS, WIDGET_BG, SCROLL_QSS,
    card_style, titulo_style, sec_style, campo_style
)


class ConsultaView(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(WIDGET_BG)
        self._rol   = auth_controller.current_user.rol
        self._pac   = None          # Paciente actualmente seleccionado
        self._mostrar_dx = False    # Si mostrar diagnósticos en historial
        self._setup_ui()

    # ── Helpers de rol ────────────────────────────────────────────────────────

    @property
    def _es_recepcion(self):
        return self._rol == UserRole.RECEPCION

    @property
    def _es_enfermero(self):
        return self._rol in (UserRole.ENF_TRIAGE, UserRole.ENF_ASISTENCIAL)

    @property
    def _es_medico(self):
        return self._rol in (
            UserRole.MEDICO, UserRole.MEDICINA_INTERNA,
            UserRole.ADMIN, UserRole.DIRECTOR
        )

    # ── Setup principal ───────────────────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 20, 32, 20)
        layout.setSpacing(12)

        # Título
        enc = QHBoxLayout()
        enc.addWidget(QLabel("Consulta de Expedientes", styleSheet=titulo_style()))
        enc.addStretch()
        layout.addLayout(enc)

        # Barra de búsqueda
        # "Ver Todos" SOLO para recepción y enfermería — médico NO (Ley 81)
        busq = QFrame()
        busq.setStyleSheet(
            f"QFrame{{background:{WHITE};border-radius:12px;border:1px solid {BORDER};}}"
        )
        bl = QHBoxLayout(busq); bl.setContentsMargins(14, 10, 14, 10); bl.setSpacing(10)
        self.inp_buscar = QLineEdit()
        self.inp_buscar.setPlaceholderText("Buscar por cédula, nombre o apellido...")
        self.inp_buscar.setStyleSheet(INPUT_QSS)
        self.inp_buscar.returnPressed.connect(self._buscar)
        btn_b = btn_buscar("Buscar"); btn_b.clicked.connect(self._buscar)
        bl.addWidget(self.inp_buscar); bl.addWidget(btn_b)
        if not self._es_medico:
            btn_t = btn_secondary("Ver Todos"); btn_t.clicked.connect(self._todos)
            bl.addWidget(btn_t)
        layout.addWidget(busq)

        # Splitter: tabla izquierda | panel derecho
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Tabla de resultados ───────────────────────────────────────────────
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(4)
        if self._es_recepcion:
            self.tabla.setHorizontalHeaderLabels(["ID", "Cédula", "Nombre", "Teléfono"])
        elif self._es_enfermero:
            self.tabla.setHorizontalHeaderLabels(["ID", "Cédula", "Nombre", "Sangre"])
        else:
            self.tabla.setHorizontalHeaderLabels(["ID", "Cédula", "Nombre", "Visitas"])
        self.tabla.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setShowGrid(False)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setStyleSheet(TABLA_QSS)
        self.tabla.itemSelectionChanged.connect(self._seleccionar)
        splitter.addWidget(self.tabla)

        # ── Panel derecho ─────────────────────────────────────────────────────
        der = QWidget(); der.setStyleSheet("background:transparent;")
        dl = QVBoxLayout(der); dl.setContentsMargins(0, 0, 0, 0); dl.setSpacing(6)

        lbl_tit = QLabel("INFORMACIÓN DEL PACIENTE")
        lbl_tit.setStyleSheet(sec_style())
        dl.addWidget(lbl_tit)

        # Stack: 0 = placeholder, 1 = contenido
        self.stack = QStackedWidget(); self.stack.setStyleSheet("background:transparent;")

        # Página 0: placeholder
        ph = QFrame()
        ph.setStyleSheet(
            f"QFrame{{background:{WHITE};border-radius:14px;border:1px solid {BORDER};}}"
        )
        phl = QVBoxLayout(ph); phl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ico = QLabel("🔍"); ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ico.setStyleSheet("font-size:40px;background:transparent;border:none;")
        lbl_ph = QLabel("Busque y seleccione\nun paciente para ver su información")
        lbl_ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_ph.setWordWrap(True)
        lbl_ph.setStyleSheet(
            f"color:{MUTED};font-size:14px;background:transparent;border:none;"
        )
        phl.addWidget(ico); phl.addSpacing(12); phl.addWidget(lbl_ph)
        self.stack.addWidget(ph)   # índice 0

        # Página 1: panel con los 3 contenedores
        self.panel = self._crear_panel()
        self.stack.addWidget(self.panel)   # índice 1
        self.stack.setCurrentIndex(0)

        dl.addWidget(self.stack)
        splitter.addWidget(der)
        splitter.setSizes([380, 640])
        layout.addWidget(splitter, stretch=1)

    # ── Panel con 3 contenedores ──────────────────────────────────────────────

    def _crear_panel(self) -> QWidget:
        outer = QWidget(); outer.setStyleSheet(f"background:{WHITE};")
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            f"QScrollArea{{background:{WHITE};border:1px solid {BORDER};"
            f"border-radius:14px;}}"
        )
        cont = QWidget(); cont.setStyleSheet(f"background:{WHITE};")
        lay = QVBoxLayout(cont); lay.setContentsMargins(18, 16, 18, 16); lay.setSpacing(14)

        # Nombre del paciente
        self.lbl_nombre = QLabel("")
        self.lbl_nombre.setStyleSheet(
            f"color:{NAVY};font-size:17px;font-weight:800;"
            f"border-bottom:2px solid {TEAL};padding-bottom:8px;background:transparent;"
        )
        lay.addWidget(self.lbl_nombre)

        # ── CONTENEDOR A: Datos Personales ────────────────────────────────────
        self.cont_a = QFrame()
        self.cont_a.setStyleSheet(
            f"QFrame{{background:#F7FAFC;border-radius:10px;border:1px solid {BORDER};}}"
        )
        a_l = QVBoxLayout(self.cont_a); a_l.setContentsMargins(14, 12, 14, 12); a_l.setSpacing(8)

        lbl_a = QLabel("📋  DATOS PERSONALES")
        lbl_a.setStyleSheet(
            f"font-size:11px;font-weight:700;color:{MUTED};"
            "letter-spacing:1px;background:transparent;"
        )
        a_l.addWidget(lbl_a)

        self.txt_a = QTextBrowser()
        self.txt_a.setStyleSheet(
            f"QTextBrowser{{background:transparent;border:none;"
            f"font-size:13px;color:{TEXT};}}"
        )
        self.txt_a.setMaximumHeight(170)
        a_l.addWidget(self.txt_a)

        # Botón editar contacto — solo Recepción
        self.btn_editar = btn_teal("✏️  Editar Contacto")
        self.btn_editar.clicked.connect(self._dlg_editar_contacto)
        self.btn_editar.setVisible(False)   # se activa solo para recepción
        a_l.addWidget(self.btn_editar)
        lay.addWidget(self.cont_a)

        # ── CONTENEDOR B: Datos Clínicos Básicos ──────────────────────────────
        self.cont_b = QFrame()
        self.cont_b.setStyleSheet(
            f"QFrame{{background:#FFF8F0;border-radius:10px;border:1px solid {BORDER};}}"
        )
        b_l = QVBoxLayout(self.cont_b); b_l.setContentsMargins(14, 12, 14, 12); b_l.setSpacing(8)

        lbl_b = QLabel("🩺  DATOS CLÍNICOS BÁSICOS")
        lbl_b.setStyleSheet(
            f"font-size:11px;font-weight:700;color:{MUTED};"
            "letter-spacing:1px;background:transparent;"
        )
        b_l.addWidget(lbl_b)

        self.txt_b = QTextBrowser()
        self.txt_b.setStyleSheet(
            f"QTextBrowser{{background:transparent;border:none;"
            f"font-size:13px;color:{TEXT};}}"
        )
        self.txt_b.setMaximumHeight(150)
        b_l.addWidget(self.txt_b)

        # Botón actualizar datos clínicos — solo Enfermería
        self.btn_clinicos = btn_teal("✏️  Actualizar Datos Clínicos")
        self.btn_clinicos.clicked.connect(self._dlg_actualizar_clinicos)
        self.btn_clinicos.setVisible(False)  # se activa solo para enfermería
        b_l.addWidget(self.btn_clinicos)
        lay.addWidget(self.cont_b)

        # ── CONTENEDOR C: Historial de Visitas ────────────────────────────────
        self.cont_c = QFrame()
        self.cont_c.setStyleSheet(
            f"QFrame{{background:{WHITE};border-radius:10px;border:1px solid {BORDER};}}"
        )
        c_l = QVBoxLayout(self.cont_c); c_l.setContentsMargins(14, 12, 14, 12); c_l.setSpacing(8)

        lbl_c = QLabel("📋  HISTORIAL DE VISITAS")
        lbl_c.setStyleSheet(
            f"font-size:11px;font-weight:700;color:{MUTED};"
            "letter-spacing:1px;background:transparent;"
        )
        c_l.addWidget(lbl_c)

        self.tabla_vis = QTableWidget(); self.tabla_vis.setColumnCount(3)
        self.tabla_vis.setHorizontalHeaderLabels(["#", "Fecha", "Estado"])
        self.tabla_vis.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabla_vis.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_vis.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_vis.verticalHeader().setVisible(False)
        self.tabla_vis.setShowGrid(False)
        self.tabla_vis.setAlternatingRowColors(True)
        self.tabla_vis.setStyleSheet(TABLA_QSS)
        self.tabla_vis.setMaximumHeight(160)
        self.tabla_vis.itemSelectionChanged.connect(self._ver_detalle_visita)
        c_l.addWidget(self.tabla_vis)

        # Detalle de la visita seleccionada (oculto hasta que hagan clic)
        self.txt_vis_det = QTextBrowser()
        self.txt_vis_det.setStyleSheet(
            f"QTextBrowser{{background:#F8FAFD;border:1px solid {BORDER};"
            f"border-radius:8px;font-size:13px;color:{TEXT};padding:10px;}}"
        )
        self.txt_vis_det.setMaximumHeight(220)
        self.txt_vis_det.setVisible(False)
        c_l.addWidget(self.txt_vis_det)
        lay.addWidget(self.cont_c)

        scroll.setWidget(cont)
        ol = QVBoxLayout(outer); ol.setContentsMargins(0, 0, 0, 0); ol.addWidget(scroll)
        return outer

    # ── Búsqueda ──────────────────────────────────────────────────────────────

    def _buscar(self):
        t = self.inp_buscar.text().strip()
        if t:
            self._poblar(paciente_controller.buscar_pacientes(t))

    def _todos(self):
        self._poblar(paciente_controller.obtener_todos_pacientes())

    def _poblar(self, pacientes):
        self.tabla.setRowCount(0); self.tabla.setRowCount(len(pacientes))
        self.stack.setCurrentIndex(0)
        self._pac = None

        for i, p in enumerate(pacientes):
            self.tabla.setItem(i, 0, QTableWidgetItem(str(p.id)))
            self.tabla.setItem(i, 1, QTableWidgetItem(p.cedula))
            self.tabla.setItem(i, 2, QTableWidgetItem(p.nombre_completo))
            if self._es_recepcion:
                self.tabla.setItem(i, 3, QTableWidgetItem(p.telefono or "—"))
            elif self._es_enfermero:
                ts = p.tipo_sangre.value if p.tipo_sangre else "—"
                self.tabla.setItem(i, 3, QTableWidgetItem(ts))
            else:
                self.tabla.setItem(i, 3, QTableWidgetItem(str(len(p.visitas))))
            self.tabla.item(i, 0).setData(Qt.ItemDataRole.UserRole, p)

    # ── Selección de paciente ─────────────────────────────────────────────────

    def _seleccionar(self):
        if not self.tabla.selectedItems():
            self.stack.setCurrentIndex(0); return
        p = self.tabla.item(self.tabla.currentRow(), 0).data(Qt.ItemDataRole.UserRole)
        if not p:
            self.stack.setCurrentIndex(0); return

        self._pac = p
        self._cargar_panel(p)
        self.stack.setCurrentIndex(1)

    # ── Carga diferenciada por rol ────────────────────────────────────────────

    def _cargar_panel(self, p):
        self.lbl_nombre.setText(p.nombre_completo)
        self.txt_vis_det.setVisible(False)

        # ── RECEPCIÓN ─────────────────────────────────────────────────────────
        if self._es_recepcion:
            # A: visible + editable
            self.cont_a.setVisible(True)
            self.btn_editar.setVisible(True)
            self._fill_a(p)
            # B y C: OCULTOS completamente
            self.cont_b.setVisible(False)
            self.cont_c.setVisible(False)

        # ── ENFERMERÍA ────────────────────────────────────────────────────────
        elif self._es_enfermero:
            # A: visible, solo lectura (sin botón editar)
            self.cont_a.setVisible(True)
            self.btn_editar.setVisible(False)
            self._fill_a(p)
            # B: visible + editable
            self.cont_b.setVisible(True)
            self.btn_clinicos.setVisible(True)
            self._fill_b(p)
            # C: visible — historial sin diagnósticos
            self.cont_c.setVisible(True)
            self._fill_c(p, mostrar_dx=False)

        # ── MÉDICO / INTERNA / ADMIN / DIRECTOR ───────────────────────────────
        else:
            # A y B: visibles, solo lectura
            self.cont_a.setVisible(True)
            self.btn_editar.setVisible(False)
            self._fill_a(p)
            self.cont_b.setVisible(True)
            self.btn_clinicos.setVisible(False)
            self._fill_b(p)
            # C: acceso total con diagnósticos
            self.cont_c.setVisible(True)
            self._fill_c(p, mostrar_dx=True)

    # ── Relleno de contenedores ───────────────────────────────────────────────

    def _fill_a(self, p):
        gen = p.genero.value if p.genero else "—"
        self.txt_a.setHtml(f"""
        <table width='100%' cellspacing='0' cellpadding='5'>
            <tr>
                <td><b>Cédula:</b> {p.cedula}</td>
                <td><b>Edad:</b> {p.edad} años</td>
                <td><b>Género:</b> {gen}</td>
                <td><b>Nac.:</b> {p.nacionalidad or '—'}</td>
            </tr>
            <tr>
                <td><b>Teléfono:</b> {p.telefono or '—'}</td>
                <td colspan='3'><b>Dirección:</b> {p.direccion or '—'}</td>
            </tr>
            <tr>
                <td><b>Contacto emg.:</b> {p.contacto_emergencia or '—'}</td>
                <td colspan='3'><b>Tel. emg.:</b> {p.telefono_emergencia or '—'}</td>
            </tr>
        </table>""")

    def _fill_b(self, p):
        ts = p.tipo_sangre.value if p.tipo_sangre else "No especificado"
        self.txt_b.setHtml(f"""
        <p><b>Tipo Sangre:</b>
            <span style='background:#E6F4FF;color:{NAVY};padding:1px 8px;
                border-radius:4px;font-weight:700;'>{ts}</span>
        </p>
        <div style='background:#FFF8F0;border-left:3px solid #F6AD55;
                    padding:6px 10px;border-radius:4px;margin:6px 0'>
            <b>Alergias:</b> {p.alergias or 'Ninguna registrada'}
        </div>
        <p><b>Enf. crónicas:</b> {p.enfermedades_cronicas or 'Ninguna'}</p>
        <p><b>Medicamentos:</b> {p.medicamentos_actuales or 'Ninguno'}</p>
        <p><b>Antecedentes:</b> {p.antecedentes_familiares or 'Ninguno'}</p>""")

    def _fill_c(self, p, mostrar_dx: bool):
        """Carga la tabla de visitas. mostrar_dx controla qué se ve al hacer clic."""
        self._mostrar_dx = mostrar_dx
        self.tabla_vis.setRowCount(0); self.tabla_vis.setRowCount(len(p.visitas))
        for i, v in enumerate(p.visitas):
            self.tabla_vis.setItem(i, 0, QTableWidgetItem(str(v.id)))
            self.tabla_vis.setItem(i, 1, QTableWidgetItem(
                v.fecha_ingreso.strftime("%d/%m/%Y %H:%M")))
            self.tabla_vis.setItem(i, 2, QTableWidgetItem(
                v.estado.value if hasattr(v.estado, "value") else str(v.estado)))
            self.tabla_vis.item(i, 0).setData(Qt.ItemDataRole.UserRole, v)
        self.txt_vis_det.setVisible(False)

    # ── Detalle de visita al hacer clic ──────────────────────────────────────

    def _ver_detalle_visita(self):
        if not self.tabla_vis.selectedItems(): return
        v = self.tabla_vis.item(
            self.tabla_vis.currentRow(), 0
        ).data(Qt.ItemDataRole.UserRole)
        if not v: return

        # Signos vitales — siempre visibles para enfermería y médicos
        signos = f"""
        <div style='background:#F0FFF4;border-left:3px solid {SUCCESS};
                    padding:8px 12px;border-radius:6px;margin-bottom:8px;'>
            <b style='color:{NAVY};'>SIGNOS VITALES — {v.fecha_ingreso.strftime('%d/%m/%Y %H:%M')}</b><br/>
            <span>Presión: <b>{v.presion_arterial or '—'}</b> &nbsp;
            Temp: <b>{v.temperatura or '—'}°C</b> &nbsp;
            Sat O₂: <b>{v.saturacion_oxigeno or '—'}%</b> &nbsp;
            FC: <b>{v.frecuencia_cardiaca or '—'} bpm</b></span><br/>
            <span>Peso: <b>{v.peso_kg or '—'} kg</b> &nbsp;
            Talla: <b>{v.talla_cm or '—'} cm</b></span>
        </div>"""

        # Evolución médica — SOLO médicos, OCULTA para enfermería
        evolucion = ""
        if self._mostrar_dx:
            motivo = v.motivo_consulta or "—"
            dx     = v.diagnostico_preliminar or ""
            trat   = v.plan_tratamiento or ""
            obs    = v.observaciones or ""
            evolucion = f"""
            <div style='background:#EBF8FF;border-left:3px solid {TEAL};
                        padding:8px 12px;border-radius:6px;'>
                <b style='color:{NAVY};'>EVOLUCIÓN MÉDICA</b><br/>
                <b>Motivo:</b> {motivo}<br/>
                {f"<b>Diagnóstico:</b> {dx}<br/>" if dx else ""}
                {f"<b>Tratamiento:</b> {trat}<br/>" if trat else ""}
                {f"<b>Observaciones:</b> {obs}" if obs else ""}
            </div>"""

        self.txt_vis_det.setHtml(
            f"<html><body style='font-family:Segoe UI,Arial;font-size:13px;'>"
            f"{signos}{evolucion}</body></html>"
        )
        self.txt_vis_det.setVisible(True)

    # ── Diálogos de edición ───────────────────────────────────────────────────

    def _dlg_editar_contacto(self):
        """RECEPCIÓN: editar solo teléfono, dirección y contacto emergencia."""
        if not self._pac:
            QMessageBox.warning(self, "Atención", "Seleccione un paciente."); return

        dlg = QDialog(self); dlg.setWindowTitle("Editar Contacto")
        dlg.setMinimumWidth(420)
        lay = QVBoxLayout(dlg); lay.setSpacing(10); lay.setContentsMargins(20, 20, 20, 20)

        campos = [
            ("Teléfono",              self._pac.telefono),
            ("Dirección",             self._pac.direccion),
            ("Contacto Emergencia",   self._pac.contacto_emergencia),
            ("Tel. Emergencia",       self._pac.telefono_emergencia),
        ]
        inputs = []
        for etq, val in campos:
            lay.addWidget(QLabel(etq.upper(), styleSheet=campo_style()))
            inp = QLineEdit(val or ""); inp.setStyleSheet(INPUT_QSS)
            lay.addWidget(inp); inputs.append(inp)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            ok, msg = paciente_controller.actualizar_contacto(
                self._pac.id,
                telefono=inputs[0].text().strip(),
                direccion=inputs[1].text().strip(),
                contacto_emergencia=inputs[2].text().strip(),
                telefono_emergencia=inputs[3].text().strip(),
            )
            if ok:
                QMessageBox.information(self, "✅ Actualizado", msg)
                self._buscar()
            else:
                QMessageBox.warning(self, "⚠ Error", msg)

    def _dlg_actualizar_clinicos(self):
        """ENFERMERÍA: actualizar alergias, medicamentos, enfermedades crónicas."""
        if not self._pac:
            QMessageBox.warning(self, "Atención", "Seleccione un paciente."); return

        dlg = QDialog(self); dlg.setWindowTitle("Actualizar Datos Clínicos Básicos")
        dlg.setMinimumWidth(440)
        lay = QVBoxLayout(dlg); lay.setSpacing(10); lay.setContentsMargins(20, 20, 20, 20)

        campos = [
            ("Alergias",              self._pac.alergias),
            ("Medicamentos actuales", self._pac.medicamentos_actuales),
            ("Enfermedades crónicas", self._pac.enfermedades_cronicas),
        ]
        areas = []
        for etq, val in campos:
            lay.addWidget(QLabel(etq.upper(), styleSheet=campo_style()))
            ta = QTextEdit(val or "")
            ta.setStyleSheet(INPUT_QSS); ta.setFixedHeight(65)
            lay.addWidget(ta); areas.append(ta)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            ok, msg = paciente_controller.actualizar_datos_clinicos(
                self._pac.id,
                alergias=areas[0].toPlainText().strip(),
                medicamentos_actuales=areas[1].toPlainText().strip(),
                enfermedades_cronicas=areas[2].toPlainText().strip(),
            )
            if ok:
                QMessageBox.information(self, "✅ Actualizado", msg)
                self._buscar()
            else:
                QMessageBox.warning(self, "⚠ Error", msg)
