"""Datasets virtuales de CuboIP Analítica.

Convenciones:
- Todas las fechas se entregan en hora local (America/Mexico_City, sin zona).
  vision.* y corp.* guardan timestamptz (UTC); public.* guarda la hora local de amon.
- Se excluyen siempre los datos de simulación.
- Etiquetas y valores en español, listos para mostrarse.
- Ninguna métrica puede llamarse igual que un valor con color fijo (LABEL_COLORS): Superset
  resuelve el color de la serie por el nombre visible y el choque le hace ignorar el color
  del tablero (pasó con "Sin conexión" en cámaras).
- En tablas grandes el filtro de tiempo se empuja al SQL con Jinja (from_dttm/to_dttm)
  para no recorrer toda la tabla en el servidor compartido 10.19.5.100.
"""

TZ = "America/Mexico_City"


def _rango(col):
    """Filtro de tiempo empujado a la consulta para columnas timestamptz."""
    return (
        "{% if from_dttm %} AND " + col + " >= ('{{ from_dttm }}'::timestamp AT TIME ZONE '" + TZ + "'){% endif %}"
        "{% if to_dttm %} AND " + col + " < ('{{ to_dttm }}'::timestamp AT TIME ZONE '" + TZ + "'){% endif %}"
    )


def _dia_semana(col):
    return (f"(ARRAY['1 Lun','2 Mar','3 Mié','4 Jue','5 Vie','6 Sáb','7 Dom'])"
            f"[extract(isodow from {col})::int]")


_CORP = "coalesce(nullif(co.alias, ''), co.nombre, 'Sin corporación')"

# Metas de SLA en minutos desde la creación del folio, por prioridad.
# PROVISIONALES (2026-09-30): el cliente aún no define las suyas; cambiar aquí y reaprovisionar.
METAS_SLA = {
    #           aceptación, llegada, cierre
    "Urgente": (2, 10, 60),
    "Alta": (3, 15, 90),
    "Media": (5, 30, 180),
    "Baja": (10, 60, 480),
}
_METAS_VALUES = ", ".join(f"('{p}', {a}, {l}, {c})" for p, (a, l, c) in METAS_SLA.items())


def _familia(inc, origen):
    """Agrupa las incidencias de alarmas y botones de pánico por nombre, para que los nombres
    nuevos del catálogo (p. ej. "Alarma pánico audible") caigan solos en su grupo."""
    return f"""CASE WHEN {inc} ~* '(bot[oó]n|p[aá]nico)' THEN 'Botón de pánico'
            WHEN {inc} ~* 'alarma' AND {inc} ~* '(incendio|fuego|humo)' THEN 'Alarma de incendio'
            WHEN {inc} ~* 'alarma' AND {inc} ~* '(intrusi[oó]n|robo|perimetral)' THEN 'Alarma de intrusión'
            WHEN {inc} ~* 'alarma' OR upper({origen}) = 'ALARMA' THEN 'Otras alarmas'
            ELSE 'Otros incidentes' END"""


_ORIGEN = """CASE upper(e.origen) WHEN 'VISION' THEN 'Visión IA' WHEN '911' THEN '911' WHEN 'ALARMA' THEN 'Alarma'
            WHEN 'APP_CIUDADANA' THEN 'App ciudadana' WHEN 'MONITOREO' THEN 'Monitoreo'
            WHEN 'HIKVISION' THEN 'Control de acceso' WHEN 'MESA' THEN 'Mesa' WHEN 'TABLETA' THEN 'Tableta'
            ELSE initcap(coalesce(e.origen, 'Sin origen')) END"""

_PRIORIDAD_CAD = """CASE upper(e.prioridad) WHEN 'URGENTE' THEN 'Urgente' WHEN 'ALTA' THEN 'Alta'
            WHEN 'MEDIA' THEN 'Media' WHEN 'BAJA' THEN 'Baja' ELSE 'Sin prioridad' END"""

# Folios reales del CAD (sin simulaciones ni pruebas del backend).
_EVENTOS_REALES = """e.active AND NOT coalesce(e.simulacion, false)
   AND coalesce(upper(e.origen), '') NOT IN ('BACKEND', 'SIMULACION')"""


def _sla(minutos, meta):
    """Cumplimiento de un tramo: si ya ocurrió se compara contra la meta; si no ocurrió y la
    atención sigue abierta, está 'En curso' hasta que se pasa de la meta."""
    return f"""CASE WHEN {meta} IS NULL THEN 'Sin meta'
            WHEN {minutos} IS NOT NULL THEN CASE WHEN {minutos} <= {meta} THEN 'Cumple' ELSE 'No cumple' END
            WHEN abierto AND transcurrido > {meta} THEN 'No cumple'
            WHEN abierto THEN 'En curso'
            ELSE 'Sin registro' END"""


def _cumplimiento(tramo):
    return {"name": f"cumple_{tramo}", "label": f"Cumplimiento {tramo.replace('aceptacion', 'aceptación')} (%)",
            "sql": f"COUNT(*) FILTER (WHERE sla_{tramo} = 'Cumple')::float"
                   f" / NULLIF(COUNT(*) FILTER (WHERE sla_{tramo} IN ('Cumple', 'No cumple')), 0)",
            "format": ".0%", "description": "Sobre las atenciones ya evaluables; no cuenta las que siguen en curso ni las sin registro."}


_PRIORIDAD_IA = """CASE a.priority WHEN 'critica' THEN 'Crítica' WHEN 'alta' THEN 'Alta'
       WHEN 'media' THEN 'Media' WHEN 'baja' THEN 'Baja' ELSE initcap(a.priority) END"""

_CLASES = """CASE {c}
      WHEN 'person' THEN 'Persona' WHEN 'car' THEN 'Auto' WHEN 'truck' THEN 'Camión'
      WHEN 'bus' THEN 'Autobús' WHEN 'motorcycle' THEN 'Motocicleta' WHEN 'bicycle' THEN 'Bicicleta'
      WHEN 'dog' THEN 'Perro' WHEN 'cat' THEN 'Gato' WHEN 'bird' THEN 'Ave'
      WHEN 'backpack' THEN 'Mochila' WHEN 'handbag' THEN 'Bolso' WHEN 'suitcase' THEN 'Maleta'
      WHEN 'cell phone' THEN 'Celular' WHEN 'laptop' THEN 'Laptop' WHEN 'tv' THEN 'Pantalla'
      WHEN 'chair' THEN 'Silla' WHEN 'bottle' THEN 'Botella' WHEN 'cup' THEN 'Taza'
      WHEN 'book' THEN 'Libro' WHEN 'keyboard' THEN 'Teclado' WHEN 'knife' THEN 'Cuchillo'
      ELSE initcap(coalesce({c}, 'Sin clase')) END"""

DATASETS = [
    # ------------------------------------------------------------------ Alertas IA
    {
        "name": "cuboip_alertas_ia",
        "description": "Alertas generadas por las analíticas de video (vision.alerts), sin simulaciones.",
        "time_column": "fecha",
        "sql": f"""
SELECT a.id,
       a.seq AS numero,
       a.created_at AT TIME ZONE '{TZ}' AS fecha,
       to_char(a.created_at AT TIME ZONE '{TZ}', 'HH24') AS hora,
       {_dia_semana(f"a.created_at AT TIME ZONE '{TZ}'")} AS dia_semana,
       {_PRIORIDAD_IA} AS prioridad,
       CASE a.priority WHEN 'critica' THEN 1 WHEN 'alta' THEN 2 WHEN 'media' THEN 3 ELSE 4 END AS prioridad_orden,
       CASE a.status WHEN 'new' THEN 'Nueva' WHEN 'ack' THEN 'En atención'
            WHEN 'resolved' THEN 'Resuelta' ELSE initcap(a.status) END AS estado,
       coalesce(t.name, a.analytic, 'Sin analítica') AS analitica,
       coalesce(t.category, 'Sin categoría') AS categoria,
       {_CLASES.format(c='a.label')} AS objeto,
       coalesce(c.name, 'Sin cámara') AS camara,
       {_CORP} AS corporacion,
       CASE a.feedback WHEN 'confirmed' THEN 'Confirmada' WHEN 'false_positive' THEN 'Falso positivo'
            ELSE 'Sin calificar' END AS calificacion,
       a.acked_by AS atendida_por,
       a.resolved_by AS resuelta_por,
       CASE WHEN a.acked_at >= a.created_at THEN extract(epoch from a.acked_at - a.created_at) / 60.0 END AS min_atencion,
       CASE WHEN a.resolved_at >= a.created_at THEN extract(epoch from a.resolved_at - a.created_at) / 60.0 END AS min_resolucion,
       nullif(a.folio, -1) AS folio,
       CASE WHEN a.folio > 0 THEN 'Con folio' ELSE 'Sin folio' END AS escalada,
       a.ccm_delivered AS enviada_ccm
  FROM vision.alerts a
  LEFT JOIN vision.cameras c ON c.id = a.camera_id
  LEFT JOIN public.camaras pc ON pc.vision_id = a.camera_id
  LEFT JOIN public.corporacion co ON co.id = pc.corporacion_id
  LEFT JOIN vision.analytic_types t ON t.code = a.analytic
 WHERE NOT a.simulacion""",
        "columns": {
            "fecha": {"label": "Fecha"}, "hora": {"label": "Hora del día"}, "dia_semana": {"label": "Día"},
            "prioridad": {"label": "Prioridad"}, "estado": {"label": "Estado"}, "analitica": {"label": "Analítica"},
            "categoria": {"label": "Categoría"}, "objeto": {"label": "Objeto detectado"}, "camara": {"label": "Cámara"},
            "corporacion": {"label": "Corporación"}, "calificacion": {"label": "Calificación del operador"},
            "min_atencion": {"label": "Minutos a atención"}, "min_resolucion": {"label": "Minutos a resolución"},
            "escalada": {"label": "Escalada a folio"}, "numero": {"label": "Alerta #"},
        },
        "metrics": [
            {"name": "alertas", "label": "Alertas", "sql": "COUNT(*)", "format": ",d"},
            {"name": "alertas_pendientes", "label": "Pendientes", "sql": "COUNT(*) FILTER (WHERE estado <> 'Resuelta')", "format": ",d"},
            {"name": "alertas_criticas", "label": "Críticas y altas", "sql": "COUNT(*) FILTER (WHERE prioridad IN ('Crítica','Alta'))", "format": ",d"},
            {"name": "precision_ia", "label": "Precisión (confirmadas / calificadas)",
             "sql": "COUNT(*) FILTER (WHERE calificacion = 'Confirmada')::float / NULLIF(COUNT(*) FILTER (WHERE calificacion <> 'Sin calificar'), 0)",
             "format": ".0%"},
            {"name": "tasa_falsos", "label": "Falsos positivos (%)",
             "sql": "COUNT(*) FILTER (WHERE calificacion = 'Falso positivo')::float / NULLIF(COUNT(*) FILTER (WHERE calificacion <> 'Sin calificar'), 0)",
             "format": ".0%"},
            {"name": "mtta", "label": "Tiempo medio de atención (min)", "sql": "AVG(min_atencion) FILTER (WHERE min_atencion < 1440)", "format": ",.1f"},
            {"name": "mttr", "label": "Tiempo medio de resolución (min)", "sql": "AVG(min_resolucion) FILTER (WHERE min_resolucion < 1440)", "format": ",.1f"},
            {"name": "p90_resolucion", "label": "P90 resolución (min)",
             "sql": "percentile_cont(0.9) WITHIN GROUP (ORDER BY min_resolucion) FILTER (WHERE min_resolucion < 1440)", "format": ",.1f"},
            {"name": "tasa_escalamiento", "label": "Escaladas a folio (%)",
             "sql": "COUNT(*) FILTER (WHERE escalada = 'Con folio')::float / NULLIF(COUNT(*), 0)", "format": ".1%"},
            {"name": "camaras_con_alertas", "label": "Cámaras con alertas", "sql": "COUNT(DISTINCT camara)", "format": ",d"},
        ],
    },
    # ------------------------------------------------------------------ Detecciones IA (tabla grande, agregada por hora)
    {
        "name": "cuboip_detecciones_hora",
        "description": "Detecciones del motor de visión agregadas por hora, cámara y clase. "
                       "El filtro de tiempo del tablero se aplica dentro de la consulta.",
        "time_column": "hora_ts",
        "cache_timeout": 1800,
        "sql": f"""
SELECT date_trunc('hour', e.ts AT TIME ZONE '{TZ}') AS hora_ts,
       coalesce(c.name, 'Sin cámara') AS camara,
       {_CLASES.format(c='e.type')} AS clase,
       count(*) AS detecciones,
       count(DISTINCT e.track_id) AS objetos_unicos,
       avg(e.confidence) AS confianza_media
  FROM vision.events e
  LEFT JOIN vision.cameras c ON c.id = e.camera_id
 WHERE e.ts >= now() - interval '90 days'{_rango('e.ts')}
 GROUP BY 1, 2, 3""",
        "columns": {"hora_ts": {"label": "Hora"}, "camara": {"label": "Cámara"}, "clase": {"label": "Clase"}},
        "metrics": [
            {"name": "detecciones", "label": "Detecciones", "sql": "SUM(detecciones)", "format": ",d"},
            {"name": "objetos", "label": "Objetos únicos (tracks)", "sql": "SUM(objetos_unicos)", "format": ",d"},
            {"name": "confianza", "label": "Confianza media", "sql": "SUM(confianza_media * detecciones) / NULLIF(SUM(detecciones), 0)", "format": ".0%"},
        ],
    },
    # ------------------------------------------------------------------ Incidentes (CAD / C4)
    {
        "name": "cuboip_incidentes",
        "description": "Folios de incidentes (public.eventos) con tiempos de atención, sin simulaciones.",
        "time_column": "fecha",
        "sql": """
SELECT e.id AS folio,
       e.created_at AS fecha,
       to_char(e.created_at, 'HH24') AS hora,
       """ + _dia_semana("e.created_at") + """ AS dia_semana,
       coalesce(nullif(e.incidencia, ''), 'Sin clasificar') AS incidencia,
       coalesce(nullif(i.tipo, ''), 'Sin tipo') AS tipo_incidencia,
       """ + _familia("e.incidencia", "e.origen") + """ AS familia,
       """ + _ORIGEN + """ AS origen,
       """ + _PRIORIDAD_CAD + """ AS prioridad,
       coalesce(e.estatus, 'Sin estatus') AS estatus,
       CASE WHEN e.estatus = 'Terminado' THEN 'Cerrado'
            WHEN e.estatus IN ('Improcedente', 'Omitido', 'Cancelado') THEN 'Descartado'
            ELSE 'Abierto' END AS situacion,
       coalesce(dc.corporaciones, 'Sin despacho') AS corporaciones,
       coalesce(nullif(e.zona_zombre, ''), 'Sin zona') AS zona,
       coalesce(nullif(e.municipio, ''), 'Sin municipio') AS municipio,
       coalesce(nullif(e.colonia, ''), 'Sin colonia') AS colonia,
       coalesce(nullif(e.motivo_terminado, ''), '—') AS motivo_cierre,
       (e.reclasificacion IS NOT NULL AND e.reclasificacion <> '') AS reclasificado,
       coalesce(e.is_automatic_call, false) AS llamada_automatica,
       CASE WHEN e.latitud ~ '^-?[0-9]+(\\.[0-9]+)?$' THEN e.latitud::float END AS lat,
       CASE WHEN e.longitud ~ '^-?[0-9]+(\\.[0-9]+)?$' THEN e.longitud::float END AS lng,
       CASE WHEN e.fecha_aceptado > '2000-01-01' AND e.fecha_aceptado >= e.created_at
            THEN extract(epoch from e.fecha_aceptado - e.created_at) / 60.0 END AS min_aceptacion,
       CASE WHEN e.fecha_en_sitio > '2000-01-01' AND e.fecha_en_sitio >= e.created_at
            THEN extract(epoch from e.fecha_en_sitio - e.created_at) / 60.0 END AS min_llegada,
       CASE WHEN e.fecha_terminado > '2000-01-01' AND e.fecha_terminado >= e.created_at
            THEN extract(epoch from e.fecha_terminado - e.created_at) / 60.0 END AS min_cierre
  FROM public.eventos e
  LEFT JOIN LATERAL (SELECT tipo FROM public.incidencias ii
                      WHERE ii.incidencia = e.incidencia AND ii.active LIMIT 1) i ON true
  -- eventos.corporacion_id queda en 0: un folio puede despacharse a varias corporaciones y
  -- cada una lleva su propio seguimiento en eventos_historial (ver cuboip_despacho_corporacion).
  LEFT JOIN LATERAL (SELECT string_agg(DISTINCT """ + _CORP + """, ', ') AS corporaciones
                       FROM public.eventos_historial h JOIN public.corporacion co ON co.id = h.corporacion_id
                      WHERE h.folio = e.id AND h.corporacion_id <> 0) dc ON true
 WHERE """ + _EVENTOS_REALES,
        "columns": {
            "folio": {"label": "Folio"}, "fecha": {"label": "Fecha"}, "hora": {"label": "Hora del día"},
            "dia_semana": {"label": "Día"}, "incidencia": {"label": "Incidencia"}, "tipo_incidencia": {"label": "Tipo"},
            "origen": {"label": "Origen"}, "prioridad": {"label": "Prioridad"}, "estatus": {"label": "Estatus"},
            "situacion": {"label": "Situación"}, "zona": {"label": "Zona"},
            "familia": {"label": "Familia", "description": "Agrupa alarmas y botones de pánico; el resto queda en 'Otros incidentes'."},
            "corporaciones": {"label": "Corporaciones despachadas"},
            "municipio": {"label": "Municipio"}, "colonia": {"label": "Colonia"}, "motivo_cierre": {"label": "Motivo de cierre"},
            "min_aceptacion": {"label": "Min. a aceptación"}, "min_llegada": {"label": "Min. a llegada"},
            "min_cierre": {"label": "Min. a cierre"},
        },
        "metrics": [
            {"name": "folios", "label": "Folios", "sql": "COUNT(*)", "format": ",d"},
            {"name": "folios_abiertos", "label": "Abiertos", "sql": "COUNT(*) FILTER (WHERE situacion = 'Abierto')", "format": ",d"},
            {"name": "folios_cerrados", "label": "Cerrados", "sql": "COUNT(*) FILTER (WHERE situacion = 'Cerrado')", "format": ",d"},
            {"name": "folios_descartados", "label": "Descartados", "sql": "COUNT(*) FILTER (WHERE situacion = 'Descartado')", "format": ",d"},
            {"name": "tasa_cierre", "label": "Cerrados (%)", "sql": "COUNT(*) FILTER (WHERE situacion = 'Cerrado')::float / NULLIF(COUNT(*), 0)", "format": ".0%"},
            {"name": "prom_aceptacion", "label": "Prom. a aceptación (min)", "sql": "AVG(min_aceptacion) FILTER (WHERE min_aceptacion < 1440)", "format": ",.1f"},
            {"name": "prom_llegada", "label": "Prom. a llegada (min)", "sql": "AVG(min_llegada) FILTER (WHERE min_llegada < 1440)", "format": ",.1f"},
            {"name": "prom_cierre", "label": "Prom. a cierre (min)", "sql": "AVG(min_cierre) FILTER (WHERE min_cierre < 2880)", "format": ",.1f"},
            {"name": "llegada_5min", "label": "Llegada en < 5 min (%)",
             "sql": "COUNT(*) FILTER (WHERE min_llegada < 5)::float / NULLIF(COUNT(*) FILTER (WHERE min_llegada IS NOT NULL), 0)", "format": ".0%"},
            {"name": "urgentes", "label": "Urgentes y altas", "sql": "COUNT(*) FILTER (WHERE prioridad IN ('Urgente','Alta'))", "format": ",d"},
        ],
    },
    # ------------------------------------------------------------------ Despacho por corporación y SLA
    {
        "name": "cuboip_despacho_corporacion",
        "description": ("Una fila por folio y corporación despachada (public.eventos_historial), con tiempos de "
                        "cada corporación y cumplimiento de SLA por prioridad. Un folio con varias "
                        "corporaciones aparece una vez por cada una."),
        "time_column": "fecha",
        "sql": """
SELECT b.*,
       """ + _sla("min_aceptacion", "meta_aceptacion") + """ AS sla_aceptacion,
       """ + _sla("min_llegada", "meta_llegada") + """ AS sla_llegada,
       """ + _sla("min_cierre", "meta_cierre") + """ AS sla_cierre
  FROM (
SELECT e.id AS folio,
       e.created_at AS fecha,
       to_char(e.created_at, 'HH24') AS hora,
       """ + _dia_semana("e.created_at") + """ AS dia_semana,
       coalesce(nullif(e.incidencia, ''), 'Sin clasificar') AS incidencia,
       """ + _familia("e.incidencia", "e.origen") + """ AS familia,
       """ + _ORIGEN + """ AS origen,
       """ + _PRIORIDAD_CAD + """ AS prioridad,
       """ + _CORP + """ AS corporacion,
       d.estatus,
       CASE WHEN d.estatus = 'Terminado' THEN 'Cerrado'
            WHEN d.estatus IN ('Improcedente', 'Omitido', 'Cancelado') THEN 'Descartado'
            ELSE 'Abierto' END AS situacion,
       (d.estatus NOT IN ('Terminado', 'Improcedente', 'Omitido', 'Cancelado')
        AND coalesce(e.estatus, '') NOT IN ('Terminado', 'Improcedente', 'Omitido', 'Cancelado')) AS abierto,
       extract(epoch from (now() AT TIME ZONE '""" + TZ + """') - e.created_at) / 60.0 AS transcurrido,
       CASE WHEN d.t_acep >= e.created_at THEN extract(epoch from d.t_acep - e.created_at) / 60.0 END AS min_aceptacion,
       CASE WHEN d.t_sitio >= e.created_at THEN extract(epoch from d.t_sitio - e.created_at) / 60.0 END AS min_llegada,
       CASE WHEN d.t_fin >= e.created_at THEN extract(epoch from d.t_fin - e.created_at) / 60.0 END AS min_cierre,
       m.aceptacion AS meta_aceptacion, m.llegada AS meta_llegada, m.cierre AS meta_cierre
  FROM public.eventos e
  JOIN LATERAL (SELECT h.corporacion_id,
                       min(h.created_at) FILTER (WHERE h.etapa_despacho = 'Aceptada') AS t_acep,
                       min(h.created_at) FILTER (WHERE h.etapa_despacho = 'En Sitio') AS t_sitio,
                       min(h.created_at) FILTER (WHERE h.estatus = 'Terminado') AS t_fin,
                       (array_agg(h.estatus ORDER BY h.id DESC))[1] AS estatus
                  FROM public.eventos_historial h
                 WHERE h.folio = e.id AND h.corporacion_id <> 0 AND coalesce(h.active, true)
                 GROUP BY h.corporacion_id) d ON true
  JOIN public.corporacion co ON co.id = d.corporacion_id
  LEFT JOIN (VALUES """ + _METAS_VALUES + """) m(prioridad, aceptacion, llegada, cierre)
         ON m.prioridad = """ + _PRIORIDAD_CAD + """
 WHERE """ + _EVENTOS_REALES + """
{% if from_dttm %} AND e.created_at >= '{{ from_dttm }}'{% endif %}{% if to_dttm %} AND e.created_at < '{{ to_dttm }}'{% endif %}
) b""",
        "columns": {
            "folio": {"label": "Folio"}, "fecha": {"label": "Fecha"}, "hora": {"label": "Hora del día"},
            "dia_semana": {"label": "Día"}, "incidencia": {"label": "Incidencia"}, "familia": {"label": "Familia"},
            "origen": {"label": "Origen"}, "prioridad": {"label": "Prioridad"}, "corporacion": {"label": "Corporación"},
            "estatus": {"label": "Estatus de la corporación"}, "situacion": {"label": "Situación"},
            "abierto": {"label": "Atención abierta"}, "transcurrido": {"label": "Min. transcurridos"},
            "min_aceptacion": {"label": "Min. a aceptación"}, "min_llegada": {"label": "Min. a llegada"},
            "min_cierre": {"label": "Min. a cierre"},
            "meta_aceptacion": {"label": "Meta aceptación (min)"}, "meta_llegada": {"label": "Meta llegada (min)"},
            "meta_cierre": {"label": "Meta cierre (min)"},
            "sla_aceptacion": {"label": "SLA aceptación"}, "sla_llegada": {"label": "SLA llegada"},
            "sla_cierre": {"label": "SLA cierre"},
        },
        "metrics": [
            {"name": "despachos", "label": "Despachos", "sql": "COUNT(*)", "format": ",d",
             "description": "Atenciones folio × corporación."},
            {"name": "folios", "label": "Folios", "sql": "COUNT(DISTINCT folio)", "format": ",d"},
            _cumplimiento("aceptacion"), _cumplimiento("llegada"), _cumplimiento("cierre"),
            {"name": "fuera_llegada", "label": "Llegadas fuera de meta", "sql": "COUNT(*) FILTER (WHERE sla_llegada = 'No cumple')", "format": ",d"},
            {"name": "prom_aceptacion", "label": "Prom. a aceptación (min)", "sql": "AVG(min_aceptacion) FILTER (WHERE min_aceptacion < 1440)", "format": ",.1f"},
            {"name": "prom_llegada", "label": "Prom. a llegada (min)", "sql": "AVG(min_llegada) FILTER (WHERE min_llegada < 1440)", "format": ",.1f"},
            {"name": "prom_cierre", "label": "Prom. a cierre (min)", "sql": "AVG(min_cierre) FILTER (WHERE min_cierre < 2880)", "format": ",.1f"},
            {"name": "p90_llegada", "label": "Llegada P90 (min)",
             "sql": "percentile_cont(0.9) WITHIN GROUP (ORDER BY min_llegada) FILTER (WHERE min_llegada < 1440)", "format": ",.1f",
             "description": "9 de cada 10 llegadas ocurren en este tiempo o menos."},
        ],
    },
    # ------------------------------------------------------------------ Cámaras (inventario y salud)
    {
        "name": "cuboip_camaras",
        "description": "Inventario de cámaras con estado de video, corporación, ubicación y actividad reciente.",
        "sql": f"""
SELECT pc.id,
       pc.nombre AS camara,
       {_CORP} AS corporacion,
       coalesce(nullif(pc.zona_nombre, ''), 'Sin zona') AS zona,
       coalesce(nullif(pc.marca, ''), 'Sin marca') AS marca,
       coalesce(nullif(pc.modelo, ''), 'Sin modelo') AS modelo,
       coalesce(nullif(pc.tipo, ''), 'Sin tipo') AS tipo,
       coalesce(nullif(pc.vms, ''), 'Directo') AS vms,
       CASE WHEN pc.ptz THEN 'PTZ' ELSE 'Fija' END AS movilidad,
       CASE coalesce(vc.status, pc.video_estado) WHEN 'online' THEN 'En línea' WHEN 'offline' THEN 'Sin conexión'
            WHEN 'disabled' THEN 'Deshabilitada' ELSE 'Desconocido' END AS estado_video,
       coalesce(vc.status_changed_at AT TIME ZONE '{TZ}', pc.video_estado_cambio) AS estado_desde,
       extract(epoch from now() - coalesce(vc.status_changed_at, pc.video_estado_cambio AT TIME ZONE '{TZ}')) / 3600.0 AS horas_en_estado,
       CASE WHEN pc.lat ~ '^-?[0-9]+(\\.[0-9]+)?$' THEN pc.lat::float END AS lat,
       CASE WHEN pc.long ~ '^-?[0-9]+(\\.[0-9]+)?$' THEN pc.long::float END AS lng,
       (SELECT count(*) FROM vision.camera_analytics ca WHERE ca.camera_id = pc.vision_id AND ca.enabled) AS analiticas_activas,
       (SELECT count(*) FROM vision.alerts a WHERE a.camera_id = pc.vision_id AND NOT a.simulacion
           AND a.created_at > now() - interval '7 days') AS alertas_7d,
       (SELECT coalesce(sum(extract(epoch from r.ended_at - r.started_at)), 0) / 3600.0 FROM vision.recordings r
         WHERE r.camera_id = pc.vision_id AND r.started_at > now() - interval '7 days') AS horas_grabadas_7d
  FROM public.camaras pc
  LEFT JOIN vision.cameras vc ON vc.id = pc.vision_id
  LEFT JOIN public.corporacion co ON co.id = pc.corporacion_id
 WHERE pc.active AND coalesce(pc.status, 1) <> -1""",
        "columns": {
            "camara": {"label": "Cámara"}, "corporacion": {"label": "Corporación"}, "zona": {"label": "Zona"},
            "marca": {"label": "Marca"}, "modelo": {"label": "Modelo"}, "tipo": {"label": "Tipo"}, "vms": {"label": "VMS"},
            "movilidad": {"label": "Movilidad"}, "estado_video": {"label": "Estado de video"},
            "estado_desde": {"label": "En este estado desde"}, "horas_en_estado": {"label": "Horas en el estado"},
            "analiticas_activas": {"label": "Analíticas activas"}, "alertas_7d": {"label": "Alertas 7 días"},
            "horas_grabadas_7d": {"label": "Horas grabadas 7 días"},
        },
        "metrics": [
            {"name": "camaras", "label": "Cámaras", "sql": "COUNT(*)", "format": ",d"},
            {"name": "camaras_en_linea", "label": "Cámaras en línea", "sql": "COUNT(*) FILTER (WHERE estado_video = 'En línea')", "format": ",d"},
            {"name": "camaras_caidas", "label": "Cámaras sin conexión", "sql": "COUNT(*) FILTER (WHERE estado_video = 'Sin conexión')", "format": ",d"},
            {"name": "disponibilidad", "label": "Disponibilidad de video",
             "sql": "COUNT(*) FILTER (WHERE estado_video = 'En línea')::float / NULLIF(COUNT(*), 0)", "format": ".0%"},
            {"name": "con_analitica", "label": "Con analítica de IA (%)",
             "sql": "COUNT(*) FILTER (WHERE analiticas_activas > 0)::float / NULLIF(COUNT(*), 0)", "format": ".0%"},
            {"name": "total_analiticas", "label": "Analíticas activas", "sql": "SUM(analiticas_activas)", "format": ",d"},
            {"name": "alertas_semana", "label": "Alertas (7 días)", "sql": "SUM(alertas_7d)", "format": ",d"},
            {"name": "horas_grabadas", "label": "Horas grabadas (7 días)", "sql": "SUM(horas_grabadas_7d)", "format": ",.0f"},
        ],
    },
    # ------------------------------------------------------------------ Grabaciones
    {
        "name": "cuboip_grabaciones",
        "description": "Segmentos de grabación por cámara: horas cubiertas y almacenamiento.",
        "time_column": "inicio",
        "sql": f"""
SELECT r.started_at AT TIME ZONE '{TZ}' AS inicio,
       coalesce(c.name, 'Sin cámara') AS camara,
       coalesce(r.storage, 'local') AS almacenamiento,
       extract(epoch from r.ended_at - r.started_at) / 3600.0 AS horas,
       r.size_bytes / 1073741824.0 AS gb
  FROM vision.recordings r
  LEFT JOIN vision.cameras c ON c.id = r.camera_id
 WHERE r.ended_at IS NOT NULL""",
        "columns": {"inicio": {"label": "Inicio"}, "camara": {"label": "Cámara"}, "almacenamiento": {"label": "Almacenamiento"}},
        "metrics": [
            {"name": "horas_video", "label": "Horas de video", "sql": "SUM(horas)", "format": ",.1f"},
            {"name": "gb_video", "label": "Almacenamiento (GB)", "sql": "SUM(gb)", "format": ",.1f"},
            {"name": "segmentos", "label": "Segmentos", "sql": "COUNT(*)", "format": ",d"},
        ],
    },
    # ------------------------------------------------------------------ Placas (LPR)
    {
        "name": "cuboip_placas",
        "description": "Lecturas de placas (vision.plate_reads) con listas, marca, color y ubicación.",
        "time_column": "fecha",
        "sql": f"""
SELECT p.ts AT TIME ZONE '{TZ}' AS fecha,
       to_char(p.ts AT TIME ZONE '{TZ}', 'HH24') AS hora,
       {_dia_semana(f"p.ts AT TIME ZONE '{TZ}'")} AS dia_semana,
       coalesce(p.plate_norm, p.plate) AS placa,
       CASE p.list_hit WHEN 'black' THEN 'Lista negra' WHEN 'interest' THEN 'De interés'
            WHEN 'white' THEN 'Autorizada' ELSE 'Sin lista' END AS lista,
       coalesce(nullif(p.color, ''), 'Sin dato') AS color,
       coalesce(nullif(p.make, ''), 'Sin dato') AS marca,
       coalesce(nullif(p.body, ''), 'Sin dato') AS carroceria,
       coalesce(c.name, p.external_camera, 'Externa') AS camara,
       CASE p.source WHEN 'cuboip' THEN 'CuboIP' WHEN 'lpr_externo' THEN 'LPR externo'
            WHEN 'sense' THEN 'Sense' ELSE initcap(coalesce(p.source, 'CuboIP')) END AS fuente,
       p.confidence AS confianza,
       coalesce(p.lat, CASE WHEN pc.lat ~ '^-?[0-9]+(\\.[0-9]+)?$' THEN pc.lat::float END) AS lat,
       coalesce(p.lng, CASE WHEN pc.long ~ '^-?[0-9]+(\\.[0-9]+)?$' THEN pc.long::float END) AS lng
  FROM vision.plate_reads p
  LEFT JOIN vision.cameras c ON c.id = p.camera_id
  LEFT JOIN public.camaras pc ON pc.vision_id = p.camera_id
 WHERE NOT coalesce(p.simulacion, false)""",
        "columns": {
            "fecha": {"label": "Fecha"}, "hora": {"label": "Hora del día"}, "dia_semana": {"label": "Día"},
            "placa": {"label": "Placa"}, "lista": {"label": "Lista"}, "color": {"label": "Color"}, "marca": {"label": "Marca"},
            "carroceria": {"label": "Carrocería"}, "camara": {"label": "Cámara"}, "fuente": {"label": "Fuente"},
            "confianza": {"label": "Confianza"},
        },
        "metrics": [
            {"name": "lecturas", "label": "Lecturas", "sql": "COUNT(*)", "format": ",d"},
            {"name": "placas_unicas", "label": "Placas únicas", "sql": "COUNT(DISTINCT placa)", "format": ",d"},
            {"name": "hits_lista", "label": "Coincidencias en lista", "sql": "COUNT(*) FILTER (WHERE lista IN ('Lista negra','De interés'))", "format": ",d"},
            {"name": "confianza_lpr", "label": "Confianza media", "sql": "AVG(confianza)", "format": ".0%"},
            {"name": "recurrencia", "label": "Lecturas por placa", "sql": "COUNT(*)::float / NULLIF(COUNT(DISTINCT placa), 0)", "format": ",.2f"},
        ],
    },
    # ------------------------------------------------------------------ Velocidad
    {
        "name": "cuboip_velocidad",
        "description": "Mediciones de velocidad por zona con excesos sobre el límite.",
        "time_column": "fecha",
        "sql": f"""
SELECT s.ts AT TIME ZONE '{TZ}' AS fecha,
       coalesce(c.name, 'Sin cámara') AS camara,
       coalesce(z.name, 'Sin zona') AS zona,
       {_CLASES.format(c='s.label')} AS clase,
       s.speed_kmh AS velocidad,
       s.limit_kmh AS limite,
       CASE WHEN s.exceeded THEN 'Exceso' ELSE 'Dentro del límite' END AS resultado,
       s.plate AS placa
  FROM vision.speed_reads s
  LEFT JOIN vision.cameras c ON c.id = s.camera_id
  LEFT JOIN vision.zones z ON z.id = s.zone_id""",
        "columns": {"fecha": {"label": "Fecha"}, "camara": {"label": "Cámara"}, "zona": {"label": "Zona"},
                    "clase": {"label": "Clase"}, "velocidad": {"label": "Velocidad (km/h)"}, "resultado": {"label": "Resultado"}},
        "metrics": [
            {"name": "mediciones", "label": "Mediciones", "sql": "COUNT(*)", "format": ",d"},
            {"name": "excesos", "label": "Excesos", "sql": "COUNT(*) FILTER (WHERE resultado = 'Exceso')", "format": ",d"},
            {"name": "vel_media", "label": "Velocidad media (km/h)", "sql": "AVG(velocidad)", "format": ",.1f"},
            {"name": "vel_p85", "label": "Velocidad P85 (km/h)", "sql": "percentile_cont(0.85) WITHIN GROUP (ORDER BY velocidad)", "format": ",.1f"},
        ],
    },
    # ------------------------------------------------------------------ Aforo (cruces de línea)
    {
        "name": "cuboip_aforo",
        "description": "Conteo de personas y vehículos que cruzan las líneas de aforo, por sentido.",
        "time_column": "fecha",
        "sql": f"""
SELECT lc.ts AT TIME ZONE '{TZ}' AS fecha,
       to_char(lc.ts AT TIME ZONE '{TZ}', 'HH24') AS hora,
       coalesce(c.name, 'Sin cámara') AS camara,
       coalesce(cl.name, 'Línea') AS linea,
       {_CLASES.format(c='lc.label')} AS clase,
       CASE WHEN lc.label = 'person' THEN 'Personas' ELSE 'Vehículos' END AS grupo,
       CASE lc.direction WHEN 'a' THEN coalesce(nullif(cl.dir_a, ''), 'Sentido A')
                         WHEN 'b' THEN coalesce(nullif(cl.dir_b, ''), 'Sentido B') ELSE 'Sin sentido' END AS sentido
  FROM vision.line_crossings lc
  LEFT JOIN vision.cameras c ON c.id = lc.camera_id
  LEFT JOIN vision.count_lines cl ON cl.id = lc.line_id""",
        "columns": {"fecha": {"label": "Fecha"}, "hora": {"label": "Hora del día"}, "camara": {"label": "Cámara"},
                    "linea": {"label": "Línea"}, "clase": {"label": "Clase"}, "grupo": {"label": "Grupo"}, "sentido": {"label": "Sentido"}},
        "metrics": [
            {"name": "cruces", "label": "Cruces", "sql": "COUNT(*)", "format": ",d"},
            {"name": "personas", "label": "Personas contadas", "sql": "COUNT(*) FILTER (WHERE grupo = 'Personas')", "format": ",d"},
            {"name": "vehiculos", "label": "Vehículos contados", "sql": "COUNT(*) FILTER (WHERE grupo = 'Vehículos')", "format": ",d"},
        ],
    },
    # ------------------------------------------------------------------ Control de acceso
    {
        "name": "cuboip_accesos",
        "description": "Eventos de control de acceso (Hikvision) por puerta, método y resultado.",
        "time_column": "fecha",
        "sql": f"""
SELECT ae.ts AT TIME ZONE '{TZ}' AS fecha,
       to_char(ae.ts AT TIME ZONE '{TZ}', 'HH24') AS hora,
       {_dia_semana(f"ae.ts AT TIME ZONE '{TZ}'")} AS dia_semana,
       {_CORP} AS corporacion,
       coalesce(p.nombre, 'Sin puerta') AS puerta,
       CASE ae.tipo WHEN 'concedido' THEN 'Concedido' WHEN 'denegado' THEN 'Denegado'
            WHEN 'coaccion' THEN 'Coacción' WHEN 'forzada' THEN 'Puerta forzada'
            WHEN 'abierta_tiempo' THEN 'Abierta demasiado tiempo' WHEN 'remoto' THEN 'Apertura remota'
            WHEN 'alarma' THEN 'Alarma' ELSE initcap(coalesce(ae.tipo, 'Otro')) END AS tipo,
       CASE WHEN ae.concedido THEN 'Concedido' ELSE 'Denegado' END AS resultado,
       CASE ae.metodo WHEN 'rostro' THEN 'Rostro' WHEN 'tarjeta' THEN 'Tarjeta' WHEN 'qr' THEN 'Código QR'
            WHEN 'pin' THEN 'PIN' WHEN 'huella' THEN 'Huella' WHEN 'remoto' THEN 'Remoto'
            ELSE 'Otro' END AS metodo,
       CASE WHEN ae.visita_id IS NOT NULL THEN 'Visitante' WHEN ae.empleado_id IS NOT NULL THEN 'Empleado'
            ELSE 'No identificado' END AS perfil,
       coalesce(nullif(ae.persona_nombre, ''), 'No identificado') AS persona,
       coalesce(emp.departamento, 'Sin departamento') AS departamento,
       ae.alerta
  FROM corp.acceso_eventos ae
  LEFT JOIN corp.acceso_puertas p ON p.id = ae.puerta_id
  LEFT JOIN corp.empleados emp ON emp.id = ae.empleado_id
  LEFT JOIN public.corporacion co ON co.id = ae.corporacion_id
 WHERE coalesce(ae.fuente, '') <> 'simulacion'""",
        "columns": {"fecha": {"label": "Fecha"}, "hora": {"label": "Hora del día"}, "dia_semana": {"label": "Día"},
                    "corporacion": {"label": "Corporación"}, "puerta": {"label": "Puerta"}, "tipo": {"label": "Tipo de evento"},
                    "resultado": {"label": "Resultado"}, "metodo": {"label": "Método"}, "perfil": {"label": "Perfil"},
                    "persona": {"label": "Persona"}, "departamento": {"label": "Departamento"}},
        "metrics": [
            {"name": "accesos", "label": "Eventos de acceso", "sql": "COUNT(*)", "format": ",d"},
            {"name": "denegados", "label": "Denegados", "sql": "COUNT(*) FILTER (WHERE resultado = 'Denegado')", "format": ",d"},
            {"name": "tasa_denegados", "label": "Denegados (%)", "sql": "COUNT(*) FILTER (WHERE resultado = 'Denegado')::float / NULLIF(COUNT(*), 0)", "format": ".1%"},
            {"name": "personas_unicas", "label": "Personas distintas", "sql": "COUNT(DISTINCT persona) FILTER (WHERE persona <> 'No identificado')", "format": ",d"},
            {"name": "alertas_acceso", "label": "Eventos con alerta", "sql": "COUNT(*) FILTER (WHERE alerta)", "format": ",d"},
            {"name": "sin_contacto", "label": "Accesos sin contacto (%)",
             "sql": "COUNT(*) FILTER (WHERE metodo IN ('Rostro','Código QR'))::float / NULLIF(COUNT(*), 0)", "format": ".0%"},
        ],
    },
    # ------------------------------------------------------------------ Visitas
    {
        "name": "cuboip_visitas",
        "description": "Registro de visitantes del corporativo.",
        "time_column": "fecha",
        "sql": f"""
SELECT v.created_at AT TIME ZONE '{TZ}' AS fecha,
       v.ultima_entrada AT TIME ZONE '{TZ}' AS entrada,
       {_CORP} AS corporacion,
       CASE v.estado WHEN 'preregistrada' THEN 'Preregistrada' WHEN 'dentro' THEN 'Dentro'
            WHEN 'salio' THEN 'Salió' WHEN 'cancelada' THEN 'Cancelada' WHEN 'rechazada' THEN 'Rechazada'
            ELSE initcap(v.estado) END AS estado,
       CASE v.origen WHEN 'preregistro' THEN 'Preregistro' WHEN 'recepcion' THEN 'Recepción'
            ELSE initcap(coalesce(v.origen, 'Otro')) END AS origen,
       initcap(coalesce(nullif(v.tipo, ''), 'Visita')) AS tipo,
       coalesce(nullif(v.empresa, ''), 'Particular') AS empresa,
       coalesce(nullif(v.anfitrion_nombre, ''), 'Sin anfitrión') AS anfitrion,
       CASE WHEN v.ultima_salida > v.ultima_entrada
            THEN extract(epoch from v.ultima_salida - v.ultima_entrada) / 60.0 END AS min_estancia
  FROM corp.visitas v
  LEFT JOIN public.corporacion co ON co.id = v.corporacion_id""",
        "columns": {"fecha": {"label": "Fecha de registro"}, "entrada": {"label": "Última entrada"}, "corporacion": {"label": "Corporación"},
                    "estado": {"label": "Estado"}, "origen": {"label": "Origen"}, "tipo": {"label": "Tipo"},
                    "empresa": {"label": "Empresa"}, "anfitrion": {"label": "Anfitrión"}, "min_estancia": {"label": "Minutos de estancia"}},
        "metrics": [
            {"name": "visitas", "label": "Visitas", "sql": "COUNT(*)", "format": ",d"},
            {"name": "visitas_dentro", "label": "Dentro ahora", "sql": "COUNT(*) FILTER (WHERE estado = 'Dentro')", "format": ",d"},
            {"name": "estancia_media", "label": "Estancia media (min)", "sql": "AVG(min_estancia)", "format": ",.0f"},
            {"name": "preregistro_pct", "label": "Con preregistro (%)", "sql": "COUNT(*) FILTER (WHERE origen = 'Preregistro')::float / NULLIF(COUNT(*), 0)", "format": ".0%"},
        ],
    },
    # ------------------------------------------------------------------ Paquetería
    {
        "name": "cuboip_paquetes",
        "description": "Paquetería recibida en el corporativo.",
        "time_column": "recibido",
        "sql": f"""
SELECT p.recibido_at AT TIME ZONE '{TZ}' AS recibido,
       {_CORP} AS corporacion,
       CASE p.estado WHEN 'pendiente' THEN 'Pendiente' WHEN 'entregado' THEN 'Entregado'
            WHEN 'devuelto' THEN 'Devuelto' ELSE initcap(p.estado) END AS estado,
       coalesce(nullif(p.paqueteria, ''), 'Sin paquetería') AS paqueteria,
       CASE WHEN p.entregado_at > p.recibido_at
            THEN extract(epoch from p.entregado_at - p.recibido_at) / 3600.0 END AS horas_entrega,
       CASE WHEN p.estado = 'pendiente' THEN extract(epoch from now() - p.recibido_at) / 86400.0 END AS dias_pendiente
  FROM corp.paquetes p
  LEFT JOIN public.corporacion co ON co.id = p.corporacion_id""",
        "columns": {"recibido": {"label": "Recibido"}, "corporacion": {"label": "Corporación"}, "estado": {"label": "Estado"},
                    "paqueteria": {"label": "Paquetería"}},
        "metrics": [
            {"name": "paquetes", "label": "Paquetes", "sql": "COUNT(*)", "format": ",d"},
            {"name": "paquetes_pendientes", "label": "Pendientes", "sql": "COUNT(*) FILTER (WHERE estado = 'Pendiente')", "format": ",d"},
            {"name": "horas_entrega", "label": "Horas medias a entrega", "sql": "AVG(horas_entrega)", "format": ",.1f"},
        ],
    },
    # ------------------------------------------------------------------ Auditoría
    {
        "name": "cuboip_auditoria",
        "description": "Bitácora de auditoría de usuarios de CuboIP (acciones, exportaciones, video, sesiones).",
        "time_column": "fecha",
        "sql": f"""
SELECT au.ts AT TIME ZONE '{TZ}' AS fecha,
       to_char(au.ts AT TIME ZONE '{TZ}', 'HH24') AS hora,
       {_dia_semana(f"au.ts AT TIME ZONE '{TZ}'")} AS dia_semana,
       coalesce(nullif(au.user_name, ''), 'Anónimo') AS usuario,
       {_CORP} AS corporacion,
       CASE au.categoria WHEN 'alta' THEN 'Alta' WHEN 'baja' THEN 'Baja' WHEN 'cambio' THEN 'Cambio'
            WHEN 'configuracion' THEN 'Configuración' WHEN 'exportacion' THEN 'Exportación'
            WHEN 'sesion' THEN 'Sesión' WHEN 'video' THEN 'Video' WHEN 'consulta' THEN 'Consulta'
            WHEN 'permisos' THEN 'Permisos' WHEN 'ptz' THEN 'PTZ' WHEN 'biometrica' THEN 'Biometría'
            ELSE initcap(coalesce(au.categoria, 'Otra')) END AS categoria,
       coalesce(au.accion, '—') AS accion,
       split_part(coalesce(au.accion, ''), '.', 1) AS modulo,
       coalesce(au.recurso, '—') AS recurso,
       CASE WHEN au.exito THEN 'Exitosa' ELSE 'Fallida' END AS resultado,
       au.duracion_ms,
       au.ip
  FROM public.auditoria_usuarios au
  LEFT JOIN public.corporacion co ON co.id = au.corporacion_id""",
        "columns": {"fecha": {"label": "Fecha"}, "hora": {"label": "Hora del día"}, "dia_semana": {"label": "Día"},
                    "usuario": {"label": "Usuario"}, "corporacion": {"label": "Corporación"}, "categoria": {"label": "Categoría"},
                    "accion": {"label": "Acción"}, "modulo": {"label": "Módulo"}, "recurso": {"label": "Recurso"},
                    "resultado": {"label": "Resultado"}, "duracion_ms": {"label": "Duración (ms)"}, "ip": {"label": "IP"}},
        "metrics": [
            {"name": "acciones", "label": "Acciones", "sql": "COUNT(*)", "format": ",d"},
            {"name": "usuarios_activos", "label": "Usuarios activos", "sql": "COUNT(DISTINCT usuario)", "format": ",d"},
            {"name": "fallidas", "label": "Fallidas", "sql": "COUNT(*) FILTER (WHERE resultado = 'Fallida')", "format": ",d"},
            {"name": "exportaciones", "label": "Exportaciones", "sql": "COUNT(*) FILTER (WHERE categoria = 'Exportación')", "format": ",d"},
            {"name": "sesiones_fallidas", "label": "Inicios de sesión fallidos", "sql": "COUNT(*) FILTER (WHERE accion = 'sesion.fallo')", "format": ",d"},
            {"name": "latencia_p95", "label": "Latencia P95 (ms)", "sql": "percentile_cont(0.95) WITHIN GROUP (ORDER BY duracion_ms)", "format": ",.0f"},
        ],
    },
    # ------------------------------------------------------------------ Copiloto
    {
        "name": "cuboip_copiloto",
        "description": "Uso del copiloto de IA de CuboIP (preguntas, respuestas, modelo y tiempos).",
        "time_column": "fecha",
        "sql": f"""
SELECT m.creado AT TIME ZONE '{TZ}' AS fecha,
       CASE m.rol WHEN 'usuario' THEN 'Pregunta' WHEN 'asistente' THEN 'Respuesta' ELSE initcap(m.rol) END AS tipo,
       coalesce(m.modelo, '—') AS modelo,
       CASE WHEN m.degradado THEN 'Degradada' ELSE 'Completa' END AS calidad,
       m.duracion_ms,
       m.conversacion_id::text AS conversacion,
       coalesce(jsonb_array_length(CASE WHEN jsonb_typeof(m.herramientas) = 'array' THEN m.herramientas END), 0) AS herramientas_usadas
  FROM public.copiloto_mensajes m""",
        "columns": {"fecha": {"label": "Fecha"}, "tipo": {"label": "Tipo"}, "modelo": {"label": "Modelo"},
                    "calidad": {"label": "Calidad"}, "duracion_ms": {"label": "Duración (ms)"}},
        "metrics": [
            {"name": "preguntas", "label": "Preguntas", "sql": "COUNT(*) FILTER (WHERE tipo = 'Pregunta')", "format": ",d"},
            {"name": "conversaciones", "label": "Conversaciones", "sql": "COUNT(DISTINCT conversacion)", "format": ",d"},
            {"name": "resp_seg", "label": "Tiempo de respuesta (s)", "sql": "AVG(duracion_ms) FILTER (WHERE tipo = 'Respuesta') / 1000.0", "format": ",.1f"},
        ],
    },
]
