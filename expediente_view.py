"""
GAMMA — Vista del Médico General y Medicina Interna
Cola automática. Diferencia entre roles automáticamente.
"""
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QFrame, QMessageBox, QSplitter, QTableWidget,
    QTableWidgetItem, QHeaderView, QTabWidget, QScrollArea,
    QCheckBox, QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import Qt, QTimer
from src.controllers.paciente_controller import paciente_controller
from src.controllers.cola_controller import cola_controller
from src.models.models import UserRole, AreaDestino
from src.controllers.auth_controller import auth_controller
from src.views._theme import NAVY, TEAL, SUCCESS, DANGER, WHITE, BORDER, TEXT, MUTED, BG
from src.views._widgets import BannerWidget
from src.views._styles import btn_primary, btn_teal, btn_secondary
from src.views._common import (
    INPUT_QSS, WIDGET_BG, TABLA_QSS, SCROLL_QSS,
    card_style, titulo_style, sec_style, campo_style
)

TAB_QSS = f"""
    QTabWidget::pane {{background:{WHITE};border:1px solid {BORDER};border-radius:0 10px 10px 10px;}}
    QTabBar::tab {{background:#EDF2F7;color:{MUTED};border:1px solid {BORDER};border-bottom:none;
        border-radius:8px 8px 0 0;padding:9px 18px;font-size:13px;font-weight:600;margin-right:2px;}}
    QTabBar::tab:selected {{background:{WHITE};color:{NAVY};border-top:3px solid {TEAL};font-weight:700;}}
    QTabBar::tab:hover {{background:#E2E8F0;color:{NAVY};}}
"""

ESTILO_RW = (
    f"QTextEdit{{background:{WHITE};border:1.5px solid {BORDER};"
    f"border-radius:8px;padding:8px 12px;font-size:13px;"
    f"color:{TEXT};min-height:120px;}}"
    f"QTextEdit:focus{{border-color:{TEAL};}}"
)
ESTILO_RO = (
    f"QTextEdit{{background:#F7FAFC;border:1.5px solid {BORDER};"
    f"border-radius:8px;padding:8px 12px;font-size:13px;"
    f"color:{MUTED};min-height:120px;}}"
)


def _lbl(t):
    l = QLabel(t.upper()); l.setStyleSheet(campo_style()); return l

def _te(ph, min_h=120):
    t = QTextEdit(); t.setPlaceholderText(ph)
    t.setMinimumHeight(min_h)
    t.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
    t.setStyleSheet(ESTILO_RW)
    return t


class ExpedienteView(QWidget):
    def __init__(self):
        super().__init__()
        self._cola_sel  = None
        self._visita_id = None
        self._rol = auth_controller.current_user.rol

        if self._rol == UserRole.MEDICINA_INTERNA:
            self._area_cola = AreaDestino.MEDICINA_INTERNA
            self._titulo    = "Medicina Interna — Cola de Pacientes"
            self._color1    = "#553C9A"
            self._color2    = "#6B46C1"
        else:
            self._area_cola = AreaDestino.MEDICINA_GENERAL
            self._titulo    = "Evaluación Clínica — Cola de Pacientes"
            self._color1    = "#276749"
            self._color2    = "#38A169"

        self.setStyleSheet(WIDGET_BG)
        self._setup_ui()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._cargar_cola)
        self._timer.start(30000)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 20, 32, 20)
        root.setSpacing(12)

        enc = QHBoxLayout()
        enc.addWidget(QLabel("Evaluación Clínica", styleSheet=titulo_style()))
        enc.addStretch()
        root.addLayout(enc)

        root.addWidget(BannerWidget("🩺", self._titulo, "", self._color1, self._color2))

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # ── Cola izquierda ────────────────────────────────────────────────────
        left = QFrame(); left.setStyleSheet(card_style())
        ll = QVBoxLayout(left); ll.setContentsMargins(14, 14, 14, 14); ll.setSpacing(10)

        lbl_c = QLabel("PACIENTES EN ESPERA")
        lbl_c.setStyleSheet(
            f"font-size:11px;font-weight:700;color:{MUTED};letter-spacing:1px;"
            f"padding-bottom:8px;border-bottom:2px solid {TEAL};background:transparent;"
        )
        ll.addWidget(lbl_c)

        nota = QLabel("🖱  Clic en un paciente para atenderlo")
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

        btn_ref = btn_secondary("↻  Actualizar")
        btn_ref.clicked.connect(self._cargar_cola)
        ll.addWidget(btn_ref)
        splitter.addWidget(left)

        # ── Panel derecho: Tabs ───────────────────────────────────────────────
        right = QWidget(); right.setStyleSheet(f"background:{BG};")
        rl = QVBoxLayout(right); rl.setContentsMargins(0, 0, 0, 0)
        tabs = QTabWidget(); tabs.setStyleSheet(TAB_QSS)
        tabs.addTab(self._tab_eval(),       "📋  Evaluación Clínica")
        tabs.addTab(self._tab_expediente(), "📂  Expediente Completo")
        rl.addWidget(tabs)
        splitter.addWidget(right)
        splitter.setSizes([300, 720])
        root.addWidget(splitter, stretch=1)

        self._cargar_cola()

    # ── TAB 1 ─────────────────────────────────────────────────────────────────

    def _tab_eval(self):
        outer = QWidget(); outer.setStyleSheet(f"background:{WHITE};")
        ol = QVBoxLayout(outer); ol.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"QScrollArea{{background:{WHITE};border:none;}}")
        cont = QWidget(); cont.setStyleSheet(f"background:{WHITE};")
        lay = QVBoxLayout(cont); lay.setContentsMargins(20, 16, 20, 20); lay.setSpacing(16)

        lay.addWidget(QLabel("DATOS DEL PACIENTE", styleSheet=sec_style()))
        self.lbl_triage = QLabel("Seleccione un paciente de la cola.")
        self.lbl_triage.setWordWrap(True)
        self.lbl_triage.setStyleSheet(
            f"color:{MUTED};font-size:12px;background:#F8FAFD;"
            f"border-radius:8px;padding:12px 14px;border:1px solid {BORDER};"
        )
        lay.addWidget(self.lbl_triage)

        self.lbl_cerrada = QLabel(
            "🔒  Evaluación CERRADA — Solo lectura (ISO 27799)."
        )
        self.lbl_cerrada.setWordWrap(True)
        self.lbl_cerrada.setStyleSheet(
            "color:#744210;font-size:12px;font-weight:700;"
            "background:#FFFBEB;border-radius:8px;"
            "padding:10px 14px;border-left:4px solid #F6AD55;"
        )
        self.lbl_cerrada.setVisible(False)
        lay.addWidget(self.lbl_cerrada)

        lay.addWidget(QLabel("EVALUACIÓN CLÍNICA", styleSheet=sec_style()))

        fila = QHBoxLayout(); fila.setSpacing(16)
        col_dia = QVBoxLayout(); col_dia.setSpacing(6)
        col_dia.addWidget(_lbl("Diagnóstico Preliminar *"))
        self.inp_dia = _te("Diagnóstico del médico...")
        col_dia.addWidget(self.inp_dia)
        col_tra = QVBoxLayout(); col_tra.setSpacing(6)
        col_tra.addWidget(_lbl("Plan de Tratamiento"))
        self.inp_tra = _te("Plan de tratamiento...")
        col_tra.addWidget(self.inp_tra)
        fila.addLayout(col_dia); fila.addLayout(col_tra)
        lay.addLayout(fila)

        col_obs = QVBoxLayout(); col_obs.setSpacing(6)
        col_obs.addWidget(_lbl("Observaciones"))
        self.inp_obs = _te("Observaciones clínicas...", 100)
        col_obs.addWidget(self.inp_obs)
        lay.addLayout(col_obs)

        lay.addWidget(QLabel("NOTA DURANTE CONSULTA", styleSheet=sec_style()))
        col_nota = QVBoxLayout(); col_nota.setSpacing(6)
        col_nota.addWidget(_lbl("Nota adicional"))
        self.inp_nota = _te("Notas durante la consulta...", 100)
        col_nota.addWidget(self.inp_nota)
        lay.addLayout(col_nota)

        self.chk_referir = QCheckBox("Referir a Medicina Interna al guardar")
        self.chk_referir.setStyleSheet(
            f"QCheckBox{{color:{NAVY};font-size:13px;font-weight:600;"
            f"spacing:8px;background:transparent;border:none;}}"
            f"QCheckBox::indicator{{width:18px;height:18px;border-radius:4px;"
            f"border:1.5px solid {BORDER};background:{WHITE};}}"
            f"QCheckBox::indicator:checked{{background:{TEAL};border-color:{TEAL};}}"
        )
        self.chk_referir.setVisible(self._rol == UserRole.MEDICO)
        lay.addWidget(self.chk_referir)

        br = QHBoxLayout(); br.setSpacing(10); br.addStretch()
        self.btn_nota = btn_teal("➕  Agregar Nota")
        self.btn_nota.clicked.connect(self._agregar_nota)
        self.btn_eval = btn_primary("✔  Guardar Evaluación")
        self.btn_eval.clicked.connect(self._guardar_evaluacion)
        br.addWidget(self.btn_nota); br.addWidget(self.btn_eval)
        lay.addLayout(br)
        lay.addItem(QSpacerItem(0, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        scroll.setWidget(cont)
        ol.addWidget(scroll)
        return outer

    # ── TAB 2 ─────────────────────────────────────────────────────────────────

    def _tab_expediente(self):
        w = QWidget(); w.setStyleSheet(f"background:{WHITE};")
        l = QVBoxLayout(w); l.setContentsMargins(20, 16, 20, 16)
        self.txt_exp = QTextEdit()
        self.txt_exp.setReadOnly(True)
        self.txt_exp.setStyleSheet(f"QTextEdit{{background:{WHITE};border:none;font-size:13px;color:{TEXT};}}")
        self.txt_exp.setPlaceholderText("Seleccione un paciente de la cola.")
        l.addWidget(self.txt_exp)
        return w

    # ── Cola ──────────────────────────────────────────────────────────────────

    def _cargar_cola(self):
        registros = cola_controller.obtener_cola_por_area(self._area_cola)
        self.tabla_cola.setRowCount(0)
        self.tabla_cola.setRowCount(len(registros))
        for i, r in enumerate(registros):
            self.tabla_cola.setItem(i, 0, QTableWidgetItem(str(r.id)))
            nombre = r.paciente.nombre_completo if r.paciente else f"#{r.paciente_id}"
            self.tabla_cola.setItem(i, 1, QTableWidgetItem(nombre))
            self.tabla_cola.setItem(i, 2, QTableWidgetItem(r.fecha_hora.strftime("%H:%M")))
            self.tabla_cola.item(i, 0).setData(Qt.ItemDataRole.UserRole, r)

    def _seleccionar_paciente(self):
        if not self.tabla_cola.selectedItems(): return
        r = self.tabla_cola.item(self.tabla_cola.currentRow(), 0).data(Qt.ItemDataRole.UserRole)
        if not r: return
        self._cola_sel = r
        pac = r.paciente

        for inp in [self.inp_dia, self.inp_tra, self.inp_obs, self.inp_nota]:
            inp.clear()
        self.chk_referir.setChecked(False)

        if not pac.visitas:
            self._visita_id = None
            self.lbl_triage.setText(
                pac.nombre_completo + " | " + pac.cedula + " | Sin visita de triage."
            )
            self._cargar_expediente(pac)
            return

        # ── MEDICINA INTERNA: ve datos del médico general ─────────────────────
        if self._rol == UserRole.MEDICINA_INTERNA:
            v_med = next(
                (v for v in pac.visitas if v.diagnostico_preliminar or v.plan_tratamiento),
                pac.visitas[0]
            )
            v_tri = next(
                (v for v in reversed(pac.visitas) if v.presion_arterial or v.temperatura),
                pac.visitas[-1]
            )
            self._visita_id = v_med.id

            info = (
                pac.nombre_completo + " | Cedula: " + pac.cedula +
                " | Edad: " + str(pac.edad) + " anos\n"
                "── SIGNOS VITALES (Triage) ──\n"
                "Presion: " + str(v_tri.presion_arterial or "--") +
                "  Temp: " + str(v_tri.temperatura or "--") + "C" +
                "  Sat O2: " + str(v_tri.saturacion_oxigeno or "--") + "%" +
                "  FC: " + str(v_tri.frecuencia_cardiaca or "--") + " bpm\n"
                "── MEDICO GENERAL ──\n"
                "Dx: " + str(v_med.diagnostico_preliminar or "Sin diagnostico") + "\n"
                "Plan: " + str(v_med.plan_tratamiento or "Sin plan") + "\n"
                "Obs: " + str(v_med.observaciones or "--")
            )
            if r.notas:
                info += "\n" + r.notas

            self.lbl_triage.setText(info)
            self.lbl_triage.setStyleSheet(
                f"color:{TEXT};font-size:12px;background:#EBF8FF;"
                f"border-radius:8px;padding:12px 14px;border-left:3px solid {TEAL};"
            )
            self.lbl_cerrada.setVisible(False)
            for inp in [self.inp_dia, self.inp_tra, self.inp_obs, self.inp_nota]:
                inp.setReadOnly(False)
                inp.setStyleSheet(ESTILO_RW)
            self.btn_eval.setEnabled(True)
            self.btn_nota.setEnabled(True)

        # ── MÉDICO GENERAL ────────────────────────────────────────────────────
        else:
            v = pac.visitas[0]
            self._visita_id = v.id
            cerrada = getattr(v, "evaluacion_cerrada", False)

            info = (
                pac.nombre_completo + " | Cedula: " + pac.cedula +
                " | Edad: " + str(pac.edad) + " anos\n"
                "Presion: " + str(v.presion_arterial or "--") +
                "  Temp: " + str(v.temperatura or "--") + "C" +
                "  Sat O2: " + str(v.saturacion_oxigeno or "--") + "%" +
                "  FC: " + str(v.frecuencia_cardiaca or "--") + " bpm" +
                "  Peso: " + str(v.peso_kg or "--") + " kg" +
                "  Talla: " + str(v.talla_cm or "--") + " cm"
            )
            self.lbl_triage.setText(info)
            self.lbl_triage.setStyleSheet(
                f"color:{TEXT};font-size:12px;background:#F8FAFD;"
                f"border-radius:8px;padding:12px 14px;border:1px solid {BORDER};"
            )
            self.lbl_cerrada.setVisible(cerrada)
            for inp in [self.inp_dia, self.inp_tra, self.inp_obs, self.inp_nota]:
                inp.setReadOnly(cerrada)
                inp.setStyleSheet(ESTILO_RO if cerrada else ESTILO_RW)
            self.btn_eval.setEnabled(not cerrada)
            self.btn_nota.setEnabled(not cerrada)

            if v.diagnostico_preliminar: self.inp_dia.setPlainText(v.diagnostico_preliminar)
            if v.plan_tratamiento:       self.inp_tra.setPlainText(v.plan_tratamiento)
            if v.observaciones:          self.inp_obs.setPlainText(v.observaciones)

        self._cargar_expediente(pac)

    # ── Expediente ────────────────────────────────────────────────────────────

    def _cargar_expediente(self, p):
        ts  = p.tipo_sangre.value if p.tipo_sangre else "--"
        gen = p.genero.value if p.genero else "--"
        vh  = ""
        for v in p.visitas:
            cerrada = getattr(v, "evaluacion_cerrada", False)
            estado  = "CERRADA" if cerrada else (
                v.estado.value if hasattr(v.estado, "value") else str(v.estado))
            vh += (
                f"<div style='background:#F7FAFC;border-left:3px solid {NAVY};"
                f"padding:10px 14px;margin-bottom:8px;border-radius:6px;'>"
                f"<b style='color:{NAVY};'>Visita #{v.id}</b> "
                f"<span style='font-size:11px;color:{MUTED};'>{estado}</span><br/>"
                f"<span style='color:{MUTED};font-size:11px;'>"
                f"{v.fecha_ingreso.strftime('%d/%m/%Y %H:%M')}</span><br/>"
                f"<b>Motivo:</b> {v.motivo_consulta[:120]}"
                + (f"<br/><b>Dx:</b> {v.diagnostico_preliminar}" if v.diagnostico_preliminar else "")
                + (f"<br/><b>Plan:</b> {v.plan_tratamiento}" if v.plan_tratamiento else "")
                + "</div>"
            )
        self.txt_exp.setHtml(
            f"<html><body style='font-family:Segoe UI,Arial;color:{TEXT};font-size:13px;'>"
            f"<h2 style='color:{NAVY};border-bottom:2px solid {TEAL};padding-bottom:8px;'>"
            f"{p.nombre_completo}</h2>"
            f"<div style='background:#F7FAFC;border-radius:8px;padding:14px;margin-bottom:12px;'>"
            f"<table width='100%' cellspacing='0' cellpadding='5'>"
            f"<tr><td><b>Cedula:</b> {p.cedula}</td>"
            f"<td><b>Edad:</b> {p.edad} anos</td>"
            f"<td><b>Genero:</b> {gen}</td>"
            f"<td><b>Sangre:</b> {ts}</td></tr>"
            f"<tr><td><b>Tel:</b> {p.telefono or '--'}</td>"
            f"<td colspan='3'><b>Dir:</b> {p.direccion or '--'}</td></tr>"
            f"</table></div>"
            f"<div style='background:#FFF8F0;border-left:3px solid #F6AD55;"
            f"padding:8px 12px;border-radius:4px;margin-bottom:8px;'>"
            f"<b>Alergias:</b> {p.alergias or 'Ninguna'}</div>"
            f"<p><b>Enf. cronicas:</b> {p.enfermedades_cronicas or 'Ninguna'}</p>"
            f"<p style='margin-bottom:12px'><b>Medicamentos:</b> {p.medicamentos_actuales or 'Ninguno'}</p>"
            f"<h3 style='color:{NAVY};font-size:12px;border-bottom:1px solid {BORDER};"
            f"padding-bottom:6px;margin-bottom:8px;'>HISTORIAL ({len(p.visitas)})</h3>"
            + (vh or f"<p style='color:{MUTED}'>Sin visitas.</p>") +
            "</body></html>"
        )

    # ── Guardar ───────────────────────────────────────────────────────────────

    def _guardar_evaluacion(self):
        if not self._cola_sel:
            QMessageBox.warning(self, "Atencion", "Seleccione un paciente."); return
        if not self._visita_id:
            QMessageBox.warning(self, "Atencion", "Sin visita de triage."); return
        diag = self.inp_dia.toPlainText().strip()
        if not diag:
            QMessageBox.warning(self, "Atencion", "El diagnostico es obligatorio."); return

        ok, msg = paciente_controller.guardar_evaluacion_clinica(
            self._visita_id, diag,
            self.inp_tra.toPlainText().strip(),
            self.inp_obs.toPlainText().strip()
        )
        if not ok:
            QMessageBox.warning(self, "Error", msg); return

        for inp in [self.inp_dia, self.inp_tra, self.inp_obs]:
            inp.setReadOnly(True); inp.setStyleSheet(ESTILO_RO)
        self.btn_eval.setEnabled(False)

        if self.chk_referir.isChecked():
            ok_r, msg_r = cola_controller.referir_a_medicina_interna(
                self._cola_sel.paciente_id, self._visita_id
            )
            msg += "\n" + msg_r

        QMessageBox.information(self, "Guardado", msg)
        self._cargar_cola()

    def _agregar_nota(self):
        if not self._visita_id:
            QMessageBox.warning(self, "Atencion", "Sin visita."); return
        cont = self.inp_nota.toPlainText().strip()
        if not cont:
            QMessageBox.warning(self, "Atencion", "Escriba la nota."); return
        ok, msg = paciente_controller.agregar_nota(self._visita_id, cont)
        if ok:
            QMessageBox.information(self, "Nota", msg); self.inp_nota.clear()
        else:
            QMessageBox.warning(self, "Error", msg)
