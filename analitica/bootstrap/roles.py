"""Roles de CuboIP Analítica. Uso: docker compose exec superset superset shell < /app/bootstrap/roles.py

- CuboIP Consulta: ve los tableros y sus datos (Gamma + acceso a la base de CuboIP). Sin SQL Lab.
- CuboIP Analista: Consulta + SQL Lab + crear gráficas y tableros propios (Alpha limitado a la base de CuboIP).
"""
from superset import db, security_manager as sm
from superset.models.core import Database

cuboip = db.session.query(Database).filter_by(database_name="CuboIP (staging)").one()
acceso_base = sm.add_permission_view_menu("database_access", cuboip.perm)


def clonar(nombre, base, extra=(), quitar=()):
    rol = sm.add_role(nombre)
    origen = sm.find_role(base)
    perms = [p for p in origen.permissions
             if not any(q in f"{p.permission.name} {p.view_menu.name}" for q in quitar)]
    rol.permissions = list({p.id: p for p in [*perms, acceso_base, *extra]}.values())
    db.session.merge(rol)
    print(f"{nombre}: {len(rol.permissions)} permisos")


sql_lab = [p for p in sm.find_role("sql_lab").permissions]
clonar("CuboIP Consulta", "Gamma", quitar=("SQL Lab", "SqlLab", "sql_json", "Query"))
clonar("CuboIP Analista", "Gamma", extra=sql_lab)
db.session.commit()
