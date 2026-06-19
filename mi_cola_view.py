"""
GAMMA — Vista Cola de Medicina Interna
Al hacer clic en un paciente:
1. Guarda paciente_id y cola_id en mi_controller (sesión activa)
2. Muestra diagnóstico del médico general en panel derecho
3. Las demás vistas MI usan el paciente activo automáticamente
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QTextBrowser, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from src.controllers.cola_controller import cola_controller
from src.controllers.mi_controller import mi_controller
from src.models.models import AreaDestino
from src.views._theme import NAVY, TEAL, SUCCESS, WHITE, BORDER, TEXT, MUTED
from src.views._widgets import BannerWidget
from src.views._styles import btn_secondary
from src.views._common import WIDGET_BG, TABLA_QSS, card_style, titulo_style, sec_style


class MIColaView(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(WIDGET_BG)
        self._setup_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._cargar_cola)
        self._timer.start(30000)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 20, 32, 20)
        layout.setSpacing(12)

        enc = QHBoxLayout()
        enc.addWidget(QLabel("Pacientes Referidos", styleSheet=titulo_style()))
        enc.addStretch()
        layout.addLayout(enc)

        layout.addWidget(BannerWidget(
            "🫀", "Medicina Interna — Cola de Pacientes Referidos", "",
            "#553C9A", "#6B46C1"
        ))

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

        nota = QLabel("🖱  Clic para seleccionar paciente activo")
        nota.setStyleSheet(
            f"color:{MUTED};font-size:11px;background:transparent;border:none;"
        )
        ll.addWidget(nota)

        self.tabla_cola = QTableWidget()
        self.tabla_cola.setColumnCount(3)
        self.tabla_cola.setHorizontalHeaderLabels(["#", "Paciente", "Hora"])
        self.tabla_cola.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabla_cola.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_cola.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_cola.verticalHeader().setVisible(False)
        self.tabla_cola.setShowGrid(False)
        self.tabla_cola.setAlternatingRowColors(True)
        self.tabla_cola.setStyleSheet(TABLA_QSS)
        self.tabla_cola.itemSelectionChanged.connect(self._seleccionar)
        ll.addWidget(self.tabla_cola)

        btn_ref = btn_secondary("↻  Actualizar Lista")
        btn_ref.clicked.connect(self._cargar_cola)
        ll.addWidget(btn_ref)
        splitter.addWidget(left)

        # ── Panel derecho: info del referido ──────────────────────────────────
        right = QFrame(); right.setStyleSheet(card_style())
        rl = QVBoxLayout(right); rl.setContentsMargins(16, 14, 16, 16); rl.setSpacing(10)

        lbl_d = QLabel("INFORMACIÓN DEL PACIENTE REFERIDO")
        lbl_d.setStyleSheet(
            f"font-size:11px;font-weight:700;color:{MUTED};letter-spacing:1px;"
            f"padding-bottom:8px;border-bottom:2px solid {TEAL};background:transparent;"
        )
        rl.addWidget(lbl_d)

        self.lbl_placeholder = QLabel(
            "Seleccione un paciente de la cola\npara ver su información y activar los módulos."
        )
        self.lbl_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_placeholder.setWordWrap(True)
        self.lbl_placeholder.setStyleSheet(
            f"color:{MUTED};font-size:14px;background:#F8FAFD;"
            f"border-radius:10px;padding:30px;border:1px solid {BORDER};"
        )
        rl.addWidget(self.lbl_placeholder)

        self.txt_detalle = QTextBrowser()
        self.txt_detalle.setStyleSheet(
            f"QTextBrowser{{background:{WHITE};border:1px solid {BORDER};"
            f"border-radius:10px;padding:14px;font-size:13px;color:{TEXT};}}"
        )
        self.txt_detalle.setVisible(False)
        rl.addWidget(self.txt_detalle, stretch=1)

        # Indicador de paciente activo
        self.lbl_activo = QLabel("")
        self.lbl_activo.setStyleSheet(
            f"color:{SUCCESS};font-size:12px;font-weight:700;"
            f"background:#F0FFF4;border-radius:8px;padding:8px 14px;"
            f"border:1px solid #9AE6B4;"
        )
        self.lbl_activo.setVisible(False)
        rl.addWidget(self.lbl_activo)

        splitter.addWidget(right)
        splitter.setSizes([320, 700])
        layout.addWidget(splitter, stretch=1)

        self._cargar_cola()

    def _cargar_cola(self):
        registros = cola_controller.obtener_cola_por_area(AreaDestino.MEDICINA_INTERNA)
        self.tabla_cola.setRowCount(0)
        self.tabla_cola.setRowCount(len(registros))
        for i, r in enumerate(registros):
            self.tabla_cola.setItem(i, 0, QTableWidgetItem(str(r.id)))
            nombre = r.paciente.nombre_completo if r.paciente else f"#{r.paciente_id}"
            self.tabla_cola.setItem(i, 1, QTableWidgetItem(nombre))
            self.tabla_cola.setItem(i, 2, QTableWidgetItem(
                r.fecha_hora.strftime("%H:%M")))
            self.tabla_cola.item(i, 0).setData(Qt.ItemDataRole.UserRole, r)

        if not registros:
            self.lbl_placeholder.setText("No hay pacientes referidos en este momento.")
            self.lbl_placeholder.setVisible(True)
            self.txt_detalle.setVisible(False)

    def _seleccionar(self):
        if not self.tabla_cola.selectedItems(): return
        r = self.tabla_cola.item(
            self.tabla_cola.currentRow(), 0
        ).data(Qt.ItemDataRole.UserRole)
        if not r: return

        # ── GUARDAR en mi_controller (sesión activa compartida) ───────────────
        ok = mi_controller.seleccionar_paciente(r)
        if not ok:
            QMessageBox.warning(self, "Error", "No se pudo cargar el paciente.")
            return

        pac = mi_controller.paciente

        # Buscar visita del médico general (con diagnóstico)
        v_med = next(
            (v for v in pac.visitas if v.diagnostico_preliminar or v.plan_tratamiento),
            pac.visitas[0] if pac.visitas else None
        )
        # Buscar signos vitales del triage
        v_tri = next(
            (v for v in reversed(pac.visitas) if v.presion_arterial or v.temperatura),
            pac.visitas[-1] if pac.visitas else None
        )

        ts  = pac.tipo_sangre.value if pac.tipo_sangre else "—"
        gen = pac.genero.value if pac.genero else "—"

        html = (
            f"<html><body style='font-family:Segoe UI,Arial;font-size:13px;color:{TEXT};'>"
            f"<h2 style='color:{NAVY};border-bottom:2px solid {TEAL};"
            f"padding-bottom:8px;margin-bottom:12px;'>{pac.nombre_completo}</h2>"
            f"<div style='background:#F7FAFC;border-radius:8px;padding:12px;margin-bottom:10px;'>"
            f"<table width='100%' cellspacing='0' cellpadding='4'>"
            f"<tr>"
            f"<td><b>Cedula:</b> {pac.cedula}</td>"
            f"<td><b>Edad:</b> {pac.edad} anos</td>"
            f"<td><b>Genero:</b> {gen}</td>"
            f"<td><b>Sangre:</b> <span style='background:#E6F4FF;color:{NAVY};"
            f"padding:1px 8px;border-radius:4px;font-weight:700;'>{ts}</span></td>"
            f"</tr>"
            f"<tr>"
            f"<td><b>Tel:</b> {pac.telefono or '—'}</td>"
            f"<td colspan='3'><b>Alergias:</b> {pac.alergias or 'Ninguna'}</td>"
            f"</tr>"
            f"</table></div>"
        )

        if v_tri:
            html += (
                f"<div style='background:#F0FFF4;border-left:3px solid {SUCCESS};"
                f"padding:10px 14px;border-radius:6px;margin-bottom:10px;'>"
                f"<b style='color:{NAVY};'>SIGNOS VITALES (Triage)</b><br/>"
                f"Presion: <b>{v_tri.presion_arterial or '—'}</b>  "
                f"Temp: <b>{v_tri.temperatura or '—'}C</b>  "
                f"Sat O2: <b>{v_tri.saturacion_oxigeno or '—'}%</b>  "
                f"FC: <b>{v_tri.frecuencia_cardiaca or '—'} bpm</b><br/>"
                f"Peso: <b>{v_tri.peso_kg or '—'} kg</b>  "
                f"Talla: <b>{v_tri.talla_cm or '—'} cm</b>"
                f"</div>"
            )

        if v_med and (v_med.diagnostico_preliminar or v_med.plan_tratamiento):
            html += (
                f"<div style='background:#EBF8FF;border-left:3px solid {TEAL};"
                f"padding:10px 14px;border-radius:6px;margin-bottom:10px;'>"
                f"<b style='color:{NAVY};'>EVALUACION MEDICO GENERAL</b><br/>"
                + (f"<b>Diagnostico:</b> {v_med.diagnostico_preliminar}<br/>"
                   if v_med.diagnostico_preliminar else "")
                + (f"<b>Plan:</b> {v_med.plan_tratamiento}<br/>"
                   if v_med.plan_tratamiento else "")
                + (f"<b>Observaciones:</b> {v_med.observaciones}"
                   if v_med.observaciones else "")
                + f"</div>"
            )

        if r.notas:
            html += (
                f"<div style='background:#FFFBEB;border-left:3px solid #F6AD55;"
                f"padding:8px 12px;border-radius:4px;font-size:12px;color:#744210;'>"
                f"{r.notas}</div>"
            )

        html += "</body></html>"
        self.txt_detalle.setHtml(html)
        self.lbl_placeholder.setVisible(False)
        self.txt_detalle.setVisible(True)

        # Mostrar indicador de paciente activo
        self.lbl_activo.setText(
            "✅  Paciente activo: " + pac.nombre_completo +
            "  — Ahora puede ir a Evolucion Medica o Enfermedades Cronicas"
        )
        self.lbl_activo.setVisible(True)
