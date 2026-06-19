"""
GAMMA — Migración: agregar tabla cola_atencion_dia y columnas nuevas.
Ejecutar UNA SOLA VEZ. NO borra datos existentes.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.database import db_manager
from sqlalchemy import text

def main():
    print("=" * 55)
    print("  GAMMA — Migración de Base de Datos")
    print("  Sin borrar datos existentes")
    print("=" * 55)

    db_manager.initialize()
    engine = db_manager._engine

    with engine.connect() as conn:

        # 1. Crear ENUMs si no existen
        print("\n[1/4] Creando tipos ENUM...")
        conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE estadocola AS ENUM ('EN_ESPERA','ATENDIDO','CANCELADO');
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
        """))
        conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE areadestino AS ENUM ('TRIAGE','MEDICINA_GENERAL','MEDICINA_INTERNA');
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
        """))
        conn.commit()
        print("  ✅ ENUMs listos")

        # 2. Crear tabla cola_atencion_dia
        print("\n[2/4] Creando tabla cola_atencion_dia...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS cola_atencion_dia (
                id             SERIAL PRIMARY KEY,
                paciente_id    INTEGER NOT NULL REFERENCES pacientes(id),
                area_destino   areadestino NOT NULL,
                estado         estadocola NOT NULL DEFAULT 'EN_ESPERA',
                fecha_hora     TIMESTAMP NOT NULL DEFAULT NOW(),
                registrado_por INTEGER REFERENCES usuarios(id),
                notas          TEXT
            );
        """))
        conn.commit()
        print("  ✅ Tabla cola_atencion_dia creada")

        # 3. Agregar columnas nuevas a visitas_medicas
        print("\n[3/4] Agregando columnas a visitas_medicas...")
        conn.execute(text("""
            ALTER TABLE visitas_medicas
            ADD COLUMN IF NOT EXISTS evaluacion_cerrada  BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS referido_a_interna  BOOLEAN NOT NULL DEFAULT FALSE;
        """))
        conn.commit()
        print("  ✅ Columnas evaluacion_cerrada y referido_a_interna agregadas")

        # 4. Verificar
        print("\n[4/4] Verificando...")
        r = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='visitas_medicas' "
            "AND column_name IN ('evaluacion_cerrada','referido_a_interna')"
        )).fetchall()
        for row in r:
            print(f"  ✅ visitas_medicas.{row[0]} OK")

        r2 = conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name='cola_atencion_dia'"
        )).scalar()
        print(f"  ✅ cola_atencion_dia existe: {bool(r2)}")

    print()
    print("=" * 55)
    print("  ✅ Migración completada. Ejecuta: python main.py")
    print("=" * 55)

if __name__ == "__main__":
    main()
