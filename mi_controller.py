"""
GAMMA — Controlador de Medicina Interna
Maneja el paciente activo de la sesión médica del especialista.
Todas las vistas MI comparten este estado.
"""
from __future__ import annotations
from src.models.models import (
    ColaAtencionDia, EstadoCola, AuditoriaLog,
    UserRole
)
from src.models.database import db_manager
from src.controllers.auth_controller import auth_controller


class MIController:
    """
    Singleton que mantiene el paciente activo para toda la sesión
    del especialista de Medicina Interna.
    Todas las vistas MI consultan _paciente_activo y _cola_id_activo.
    """

    def __init__(self):
        self._paciente_activo = None   # objeto Paciente cargado con eager load
        self._cola_id_activo  = None   # id de ColaAtencionDia activo

    # ── Getters ───────────────────────────────────────────────────────────────

    @property
    def paciente(self):
        return self._paciente_activo

    @property
    def cola_id(self):
        return self._cola_id_activo

    @property
    def tiene_paciente(self) -> bool:
        return self._paciente_activo is not None

    # ── Seleccionar paciente desde la cola ────────────────────────────────────

    def seleccionar_paciente(self, cola_entrada) -> bool:
        """
        Recibe una entrada de ColaAtencionDia ya cargada (con paciente y visitas).
        Guarda el paciente_id y cola_id como variables activas de la sesión.
        """
        if not cola_entrada or not cola_entrada.paciente:
            return False
        self._paciente_activo = cola_entrada.paciente
        self._cola_id_activo  = cola_entrada.id

        # Auditoría
        session = db_manager.get_session()
        try:
            session.add(AuditoriaLog(
                usuario_id=auth_controller.current_user.id,
                accion="EXPEDIENTE_CONSULTADO",
                tabla_afectada="pacientes",
                registro_id=self._paciente_activo.id,
                detalle=(
                    "Medicina Interna abrió expediente de "
                    + self._paciente_activo.nombre_completo
                ),
            ))
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

        return True

    def limpiar(self):
        self._paciente_activo = None
        self._cola_id_activo  = None

    # ── Cerrar caso: UPDATE cola a ATENDIDO ───────────────────────────────────

    def cerrar_caso(self) -> tuple[bool, str]:
        """
        Marca la entrada de cola como ATENDIDO y hace commit.
        Remueve al paciente de la lista de espera de Medicina Interna.
        """
        if not self._cola_id_activo:
            return False, "No hay cola activa."

        session = db_manager.get_session()
        try:
            entrada = session.get(ColaAtencionDia, self._cola_id_activo)
            if not entrada:
                return False, "Entrada de cola no encontrada."

            entrada.estado = EstadoCola.ATENDIDO   # UPDATE → ATENDIDO

            session.add(AuditoriaLog(
                usuario_id=auth_controller.current_user.id,
                accion="CASO_CERRADO_MI",
                tabla_afectada="cola_atencion_dia",
                registro_id=self._cola_id_activo,
                detalle=(
                    "Medicina Interna cerró el caso del paciente "
                    + (self._paciente_activo.nombre_completo if self._paciente_activo else "—")
                ),
            ))
            session.commit()   # ← commit explícito
            self.limpiar()
            return True, "Caso cerrado. Paciente removido de la cola."

        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()

    # ── Guardar evolución médica ───────────────────────────────────────────────

    def guardar_evolucion(self, datos: dict) -> tuple[bool, str]:
        """
        INSERT en visitas_medicas con el diagnóstico especializado.
        Luego cierra el caso automáticamente.
        """
        if not self._paciente_activo:
            return False, "No hay paciente activo."

        from src.models.models import VisitaMedica
        session = db_manager.get_session()
        try:
            visita = VisitaMedica(
                paciente_id=self._paciente_activo.id,
                medico_id=auth_controller.current_user.id,
                motivo_consulta=datos.get("motivo_consulta", "Evolución Medicina Interna"),
                diagnostico_preliminar=datos.get("diagnostico", ""),
                plan_tratamiento=datos.get("plan_tratamiento", ""),
                observaciones=datos.get("observaciones", ""),
                area_especialidad="Medicina Interna",
            )
            session.add(visita)

            session.add(AuditoriaLog(
                usuario_id=auth_controller.current_user.id,
                accion="EVALUACION_CLINICA_ACTUALIZADA",
                tabla_afectada="visitas_medicas",
                registro_id=self._paciente_activo.id,
                detalle="Evolución de Medicina Interna guardada.",
            ))
            session.commit()

            # Cerrar caso en cola
            ok, msg_cola = self.cerrar_caso()
            return True, "Evolución guardada." + (" " + msg_cola if ok else "")

        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()


# Singleton compartido por todas las vistas MI
mi_controller = MIController()
