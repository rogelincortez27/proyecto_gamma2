"""
GAMMA — Controlador de Cola de Atención del Día
Flujo: Recepción → Triage → Médico General → Medicina Interna
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import joinedload, selectinload
from src.models.models import (
    ColaAtencionDia, EstadoCola, AreaDestino,
    UserRole, AuditoriaLog, Paciente
)
from src.models.database import db_manager
from src.controllers.auth_controller import auth_controller

ROLES_RECEPCION = [UserRole.ADMIN, UserRole.RECEPCION]
ROLES_TRIAGE    = [UserRole.ADMIN, UserRole.ENF_TRIAGE]
ROLES_MEDICO    = [UserRole.ADMIN, UserRole.MEDICO, UserRole.MEDICINA_INTERNA]


class ColaController:

    def enviar_a_triage(self, paciente_id: int) -> tuple[bool, str]:
        """Recepción inserta paciente en cola con destino TRIAGE."""
        if not auth_controller.has_permission(ROLES_RECEPCION):
            return False, "Sin permisos."

        session = db_manager.get_session()
        try:
            pac = session.get(Paciente, paciente_id)
            if not pac:
                return False, "Paciente no encontrado."

            # Verificar si ya está en cola activa
            ya = (session.query(ColaAtencionDia)
                  .filter(ColaAtencionDia.paciente_id == paciente_id,
                          ColaAtencionDia.estado == EstadoCola.EN_ESPERA)
                  .first())
            if ya:
                return False, f"El paciente ya está en espera en {ya.area_destino.value}."

            entrada = ColaAtencionDia(
                paciente_id=paciente_id,
                area_destino=AreaDestino.TRIAGE,
                estado=EstadoCola.EN_ESPERA,
                registrado_por=auth_controller.current_user.id,
            )
            session.add(entrada)

            # Auditoría
            session.add(AuditoriaLog(
                usuario_id=auth_controller.current_user.id,
                accion="PACIENTE_ENVIADO_TRIAGE",
                tabla_afectada="cola_atencion_dia",
                registro_id=paciente_id,
                detalle=f"Paciente {pac.nombre_completo} enviado a Triage.",
            ))
            session.commit()   # ← commit explícito para que la enfermera lo vea
            return True, f"✅ {pac.nombre_completo} enviado a Triage."

        except Exception as e:
            session.rollback()
            return False, f"Error: {e}"
        finally:
            session.close()

    def obtener_cola_por_area(self, area: AreaDestino) -> list[ColaAtencionDia]:
        """Devuelve pacientes EN_ESPERA para un área específica con todos los datos cargados."""
        from src.models.models import Paciente, VisitaMedica, CitaMedica
        session = db_manager.get_session()
        try:
            registros = (session.query(ColaAtencionDia)
                         .options(
                             joinedload(ColaAtencionDia.paciente)
                             .selectinload(Paciente.visitas),
                             joinedload(ColaAtencionDia.paciente)
                             .selectinload(Paciente.citas),
                         )
                         .filter(ColaAtencionDia.area_destino == area,
                                 ColaAtencionDia.estado == EstadoCola.EN_ESPERA)
                         .order_by(ColaAtencionDia.fecha_hora.asc())
                         .all())
            # Mantener sesión abierta usando expunge con make_transient para cada objeto
            resultado = []
            for r in registros:
                # Forzar carga de relaciones antes de cerrar sesión
                _ = r.paciente
                if r.paciente:
                    _ = r.paciente.visitas
                    _ = r.paciente.citas
                resultado.append(r)
            session.expunge_all()
            return resultado
        finally:
            session.close()

    def pasar_a_medico(
        self, cola_id: int, datos_triage: dict,
        area_destino: AreaDestino = AreaDestino.MEDICINA_GENERAL
    ) -> tuple[bool, str]:
        """Triage guarda signos vitales y pasa paciente al médico."""
        if not auth_controller.has_permission(ROLES_TRIAGE):
            return False, "Sin permisos."

        session = db_manager.get_session()
        try:
            cola = session.get(ColaAtencionDia, cola_id)
            if not cola or cola.estado != EstadoCola.EN_ESPERA:
                return False, "Entrada de cola no válida."

            # Solo crear visita si se pasaron datos de triage
            if datos_triage:
                from src.models.models import VisitaMedica
                visita = VisitaMedica(
                    paciente_id=cola.paciente_id,
                    medico_id=auth_controller.current_user.id,
                    motivo_consulta=datos_triage.get("motivo_consulta", "Triage"),
                    presion_arterial=datos_triage.get("presion_arterial"),
                    temperatura=datos_triage.get("temperatura"),
                    saturacion_oxigeno=datos_triage.get("saturacion_oxigeno"),
                    frecuencia_cardiaca=datos_triage.get("frecuencia_cardiaca"),
                    peso_kg=datos_triage.get("peso_kg"),
                    talla_cm=datos_triage.get("talla_cm"),
                    observaciones=datos_triage.get("observaciones", ""),
                )
                session.add(visita)

            # Marcar triage como ATENDIDO
            cola.estado = EstadoCola.ATENDIDO

            # Crear nueva entrada para el médico
            nueva = ColaAtencionDia(
                paciente_id=cola.paciente_id,
                area_destino=area_destino,
                estado=EstadoCola.EN_ESPERA,
                registrado_por=auth_controller.current_user.id,
                notas=f"Viene de Triage",
            )
            session.add(nueva)

            session.add(AuditoriaLog(
                usuario_id=auth_controller.current_user.id,
                accion="TRIAGE_COMPLETADO",
                tabla_afectada="cola_atencion_dia",
                registro_id=cola.paciente_id,
                detalle=f"Paciente enviado a {area_destino.value}.",
            ))
            session.commit()
            return True, f"✅ Paciente enviado a {area_destino.value}."

        except Exception as e:
            session.rollback()
            return False, f"Error: {e}"
        finally:
            session.close()

    def referir_a_medicina_interna(self, paciente_id: int, visita_id: int) -> tuple[bool, str]:
        """Médico general refiere paciente a Medicina Interna."""
        if not auth_controller.has_permission(ROLES_MEDICO):
            return False, "Sin permisos."

        session = db_manager.get_session()
        try:
            # Marcar visita como referida
            from src.models.models import VisitaMedica
            visita = session.get(VisitaMedica, visita_id)
            if visita:
                visita.referido_a_interna = True

            # Insertar en cola de Medicina Interna
            nueva = ColaAtencionDia(
                paciente_id=paciente_id,
                area_destino=AreaDestino.MEDICINA_INTERNA,
                estado=EstadoCola.EN_ESPERA,
                registrado_por=auth_controller.current_user.id,
                notas=f"Referido por Médico General — Visita #{visita_id}",
                # El internista verá las visitas del paciente cargadas en la cola
            )
            session.add(nueva)

            session.add(AuditoriaLog(
                usuario_id=auth_controller.current_user.id,
                accion="REFERIDO_MEDICINA_INTERNA",
                tabla_afectada="cola_atencion_dia",
                registro_id=paciente_id,
                detalle=f"Referido desde visita #{visita_id}.",
            ))
            session.commit()
            return True, "✅ Paciente referido a Medicina Interna."

        except Exception as e:
            session.rollback()
            return False, f"Error: {e}"
        finally:
            session.close()


cola_controller = ColaController()
