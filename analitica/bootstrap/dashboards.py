"""Gráficas y tableros de CuboIP Analítica.

Cada tablero es una lista de filas; cada fila, una lista de celdas:
  ("md", ancho, alto, "markdown")                      -> texto
  (clave_grafica, ancho, alto)                         -> gráfica definida en CHARTS
Ancho en columnas de 12; alto en unidades de Superset (8 px).
"""
from datasets import METAS_SLA

MAPA_CLARO = "tile://https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
VISTA_CHIHUAHUA = {"longitude": -106.078, "latitude": 28.672, "zoom": 13.2, "bearing": 0, "pitch": 0}

# Colores fijos por valor: mismos en todos los tableros.
LABEL_COLORS = {
    "Crítica": "#B91C1C", "Urgente": "#B91C1C", "Alta": "#FF4D5E", "Media": "#F5B544", "Baja": "#94A3B8",
    "Sin prioridad": "#CBD5E1",
    "Nueva": "#FF4D5E", "En atención": "#F5B544", "Resuelta": "#16A34A",
    "Abierto": "#F5B544", "Cerrado": "#16A34A", "Descartado": "#94A3B8",
    "Confirmada": "#16A34A", "Falso positivo": "#FF4D5E", "Sin calificar": "#CBD5E1",
    "En línea": "#16A34A", "Sin conexión": "#DC2626", "Desconocido": "#94A3B8", "Deshabilitada": "#64748B",
    "Concedido": "#16A34A", "Denegado": "#DC2626",
    "Exitosa": "#16A34A", "Fallida": "#DC2626",
    "Exceso": "#FF4D5E", "Dentro del límite": "#34D399",
    "Lista negra": "#111827", "De interés": "#F5B544", "Autorizada": "#16A34A", "Sin lista": "#0EA5C6",
    "Personas": "#0EA5C6", "Vehículos": "#7C5CFF",
    "Visión IA": "#0EA5C6", "911": "#FF4D5E", "Alarma": "#F5B544", "App ciudadana": "#7C5CFF",
    "Pendiente": "#F5B544", "Entregado": "#16A34A", "Devuelto": "#94A3B8",
    "Dentro": "#0EA5C6", "Salió": "#16A34A", "Preregistrada": "#7C5CFF", "Cancelada": "#94A3B8",
    "En meta": "#16A34A", "Fuera de meta": "#DC2626", "Sin meta": "#94A3B8", "Sin medición": "#CBD5E1", "No aplica": "#64748B",
    "Cumplido": "#16A34A", "Incumplido": "#DC2626", "Sin protocolo": "#CBD5E1", "Sin evaluar": "#F5B544",
    "Botón de pánico": "#B91C1C", "Alarma de intrusión": "#FF4D5E", "Alarma de incendio": "#F97316",
    "Otras alarmas": "#F5B544", "Otros incidentes": "#CBD5E1",
    "Cumple": "#16A34A", "No cumple": "#DC2626", "En curso": "#F5B544", "Sin registro": "#CBD5E1", "Sin meta": "#94A3B8",
}


def _m(name):
    return name  # métrica guardada en el dataset


# ---------------------------------------------------------------------------
# Constructores de form_data
# ---------------------------------------------------------------------------
def kpi(metric, subheader="", fmt="SMART_NUMBER"):
    return ("big_number_total", {"metric": metric, "subheader": subheader, "y_axis_format": fmt,
                                 "header_font_size": 0.3, "subheader_font_size": 0.125, "time_range": "No filter"})


def kpi_trend(metric, x, grain="P1D", fmt="SMART_NUMBER", compare=None):
    p = {"metric": metric, "x_axis": x, "time_grain_sqla": grain, "y_axis_format": fmt,
         "show_trend_line": True, "start_y_axis_at_zero": True, "header_font_size": 0.3, "aggregation": "sum",
         "subheader_font_size": 0.15, "time_range": "No filter", "rolling_type": "None"}
    if compare:
        p.update({"compare_lag": compare, "compare_suffix": "vs. periodo anterior"})
    return ("big_number", p)


def serie(metrics, x, groupby=None, grain="P1D", kind="bar", stack=True, fmt="SMART_NUMBER", legend=True,
          xfmt="%d %b", area=False):
    viz = {"bar": "echarts_timeseries_bar", "line": "echarts_timeseries_line", "area": "echarts_area",
           "smooth": "echarts_timeseries_smooth"}[kind]
    return (viz, {
        "x_axis": x, "time_grain_sqla": grain, "metrics": metrics, "groupby": groupby or [],
        "stack": "Stack" if stack and groupby else None, "show_legend": legend, "legendOrientation": "top",
        "legendType": "scroll", "rich_tooltip": True, "tooltipTimeFormat": "%d/%m/%Y %H:%M",
        "x_axis_time_format": xfmt, "y_axis_format": fmt, "truncateYAxis": False, "y_axis_bounds": [None, None],
        "zoomable": False, "markerEnabled": kind in ("line", "smooth"), "markerSize": 4, "opacity": 0.35,
        "seriesType": "line", "show_value": False, "only_total": True, "time_range": "No filter",
        "row_limit": 10000, "truncate_metric": True, "sort_series_type": "sum", "sort_series_ascending": False,
    })


def barras(metric, dim, groupby=None, horizontal=True, limit=10, fmt="SMART_NUMBER", show_value=True,
           asc=False, sort_by_x=False):
    return ("echarts_timeseries_bar", {
        "x_axis": dim, "metrics": [metric], "groupby": groupby or [], "orientation": "horizontal" if horizontal else "vertical",
        "x_axis_sort": dim if sort_by_x else metric_label(metric),
        "x_axis_sort_asc": True if sort_by_x else (not asc if horizontal else asc),
        "x_axis_sort_series_type": "sum", "row_limit": limit if not groupby else 10000, "series_limit": 0,
        "stack": "Stack" if groupby else None, "show_value": show_value and not groupby, "only_total": True,
        "show_legend": bool(groupby), "legendOrientation": "top", "legendType": "scroll", "rich_tooltip": True,
        "y_axis_format": fmt, "truncateYAxis": False, "time_range": "No filter", "x_axis_title_margin": 15,
        "y_axis_title_margin": 15, "xAxisLabelRotation": 0,
    })


def dona(metric, dim, limit=8, fmt="SMART_NUMBER"):
    return ("pie", {"metric": metric, "groupby": [dim], "row_limit": limit, "donut": True, "innerRadius": 58,
                    "outerRadius": 72, "show_labels": True, "labels_outside": False, "label_type": "percent",
                    "show_legend": True, "legendOrientation": "bottom", "legendType": "scroll", "number_format": fmt, "sort_by_metric": True, "show_total": True,
                    "time_range": "No filter"})


def calor(metric, x, y, scheme="cuboip_cian", fmt="SMART_NUMBER"):
    return ("heatmap_v2", {"x_axis": x, "groupby": y, "metric": metric, "linear_color_scheme": scheme,
                           "normalize_across": "heatmap", "show_values": False, "show_legend": True,
                           "value_bounds": [None, None], "y_axis_format": fmt, "sort_x_axis": "alpha_asc",
                           "sort_y_axis": "alpha_asc", "xscale_interval": 1, "yscale_interval": 1,
                           "left_margin": "auto", "bottom_margin": "auto", "time_range": "No filter",
                           "row_limit": 10000})


def _formatos(formats):
    return {col: {"d3NumberFormat": fmt} for col, fmt in (formats or {}).items()}


def tabla(groupby, metrics, order=None, limit=50, conditional=None, page=20, formats=None):
    return ("table", {"query_mode": "aggregate", "groupby": groupby, "metrics": metrics,
                      "timeseries_limit_metric": order or metrics[0], "order_desc": True, "row_limit": limit,
                      "server_page_length": page, "include_search": True, "show_cell_bars": True,
                      "color_pn": False, "allow_rearrange_columns": True, "time_range": "No filter",
                      "conditional_formatting": conditional or [], "table_timestamp_format": "%d/%m/%Y %H:%M",
                      "column_config": _formatos(formats)})


def detalle(columns, order_col, limit=200, page=15, conditional=None, formats=None):
    return ("table", {"query_mode": "raw", "all_columns": columns, "order_by_cols": [f'["{order_col}", false]'],
                      "row_limit": limit, "server_page_length": page, "include_search": True,
                      "show_cell_bars": False, "allow_rearrange_columns": True, "time_range": "No filter",
                      "table_timestamp_format": "%d/%m/%Y %H:%M", "conditional_formatting": conditional or [],
                      "column_config": _formatos(formats)})


def embudo(metric, dim):
    return ("funnel", {"groupby": [dim], "metric": metric, "sort_by_metric": True, "row_limit": 10,
                       "show_labels": True, "label_type": "key_value_percent", "show_legend": False,
                       "number_format": "SMART_NUMBER", "time_range": "No filter"})


def medidor(metric, maximo=1, fmt=".0%", intervals="0.8,0.95,1", colors="3,4,2"):
    return ("gauge_chart", {"metric": metric, "min_val": 0, "max_val": maximo, "start_angle": 225, "end_angle": -45,
                            "number_format": fmt, "show_progress": True, "overlap": True, "round_cap": True,
                            "show_pointer": False, "animation": True, "split_number": 2,
                            "show_axis_line_ticks": False, "show_split_line": False,
                            "intervals": intervals, "interval_color_indices": colors, "font_size": 18,
                            "time_range": "No filter"})


def arbol(metric, dims):
    return ("treemap_v2", {"groupby": dims, "metric": metric, "row_limit": 200, "show_labels": True,
                           "show_upper_labels": True, "label_type": "key_value", "number_format": "SMART_NUMBER",
                           "time_range": "No filter"})


def sankey(metric, source, target):
    return ("sankey_v2", {"source": source, "target": target, "metric": metric, "row_limit": 200,
                          "time_range": "No filter"})


def mapa(lat="lat", lng="lng", color=(14, 165, 198), radius=60, dimension=None, tooltip=None):
    p = {"spatial": {"type": "latlong", "latCol": lat, "lonCol": lng}, "row_limit": 5000,
         "point_radius_fixed": {"type": "fix", "value": radius}, "point_unit": "square_m", "min_radius": 4,
         "max_radius": 30, "multiplier": 1, "mapbox_style": MAPA_CLARO, "viewport": VISTA_CHIHUAHUA,
         "autozoom": False,  # 99 % de los datos está en Chihuahua; la cámara de Puebla queda al desplazar
         "color_picker": {"r": color[0], "g": color[1], "b": color[2], "a": 0.85},
         "time_range": "No filter", "color_scheme": "cuboip"}
    if dimension:
        p["dimension"] = dimension
    if tooltip:
        p["js_tooltip"] = ""
        p["tooltip_contents"] = tooltip
    return ("deck_scatter", p)


def barras_multi(metrics, dim, limit=12, fmt=",.1f", horizontal=True, stack=True):
    """Barras con varias métricas por categoría (p. ej. tramos de tiempo apilados por incidencia)."""
    return ("echarts_timeseries_bar", {
        "x_axis": dim, "metrics": metrics, "groupby": [], "orientation": "horizontal" if horizontal else "vertical",
        "x_axis_sort": metrics[0], "x_axis_sort_asc": False, "x_axis_sort_series_type": "sum", "row_limit": limit,
        "stack": "Stack" if stack else None, "show_value": False, "only_total": True, "show_legend": True,
        "legendOrientation": "top", "legendType": "scroll", "rich_tooltip": True, "y_axis_format": fmt,
        "truncateYAxis": False, "time_range": "No filter", "xAxisLabelRotation": 0,
    })


def mapa_calor(metric, lat="lat", lng="lng", radius=40, scheme="cuboip_alarma"):
    """Mapa de calor deck.gl ponderado por la métrica (se encuadra solo a los datos)."""
    return ("deck_heatmap", {"spatial": {"type": "latlong", "latCol": lat, "lonCol": lng}, "size": metric,
                             "row_limit": 10000, "mapbox_style": MAPA_CLARO, "viewport": VISTA_CHIHUAHUA, "autozoom": True,
                             "linear_color_scheme": scheme, "intensity": 1, "radius_pixels": radius,
                             "aggregation": "SUM", "time_range": "No filter"})
def filtrado(chart, sql):
    """Agrega a la gráfica un filtro fijo en SQL sobre las columnas del dataset."""
    viz, p = chart
    return (viz, {**p, "adhoc_filters": [{"expressionType": "SQL", "clause": "WHERE", "sqlExpression": sql}]})


SOLO_ALARMAS = "familia <> 'Otros incidentes'"
FUERA_DE_META = "'No cumple' IN (sla_aceptacion, sla_llegada, sla_cierre)"


def metric_label(name):
    return name


# ---------------------------------------------------------------------------
# Gráficas: clave -> (dataset, título, (viz, params), descripción)
# ---------------------------------------------------------------------------
CHARTS = {
    # --- Alertas IA
    "al_total": ("cuboip_alertas_ia", "Alertas de IA", kpi_trend("alertas", "fecha"), "Alertas generadas en el periodo; la línea muestra el comportamiento diario."),
    "al_pend": ("cuboip_alertas_ia", "Pendientes", kpi("alertas_pendientes", "alertas sin resolver"), "Alertas nuevas o en atención."),
    "al_crit": ("cuboip_alertas_ia", "Alertas críticas y altas", kpi("alertas_criticas", "prioridad crítica o alta"), None),
    "al_mtta": ("cuboip_alertas_ia", "Atención (min)", kpi("mtta", "promedio a primera atención", ",.1f"), "Desde que se genera la alerta hasta que un operador la toma."),
    "al_mttr": ("cuboip_alertas_ia", "Resolución (min)", kpi("mttr", "promedio hasta resolver", ",.1f"), None),
    "al_prec": ("cuboip_alertas_ia", "Precisión IA", kpi("precision_ia", "confirmadas / calificadas", ".0%"), "Confirmadas entre calificadas por los operadores."),
    "al_escal": ("cuboip_alertas_ia", "Escaladas a folio", kpi("tasa_escalamiento", "alertas que generaron incidente", ".1%"), None),
    "al_dia_prio": ("cuboip_alertas_ia", "Alertas por día y prioridad", serie(["alertas"], "fecha", ["prioridad"]), None),
    "al_hora_prio": ("cuboip_alertas_ia", "Alertas por hora y prioridad", serie(["alertas"], "fecha", ["prioridad"], grain="PT1H", xfmt="%d %b %H:%M"), None),
    "al_analitica": ("cuboip_alertas_ia", "Alertas por analítica", barras("alertas", "analitica", limit=12), None),
    "al_categoria": ("cuboip_alertas_ia", "Alertas por categoría", dona("alertas", "categoria"), None),
    "al_estado": ("cuboip_alertas_ia", "Estado de las alertas", dona("alertas", "estado"), None),
    "al_calif": ("cuboip_alertas_ia", "Calificación de los operadores", dona("alertas", "calificacion"), None),
    "al_calor": ("cuboip_alertas_ia", "Mapa de calor: día y hora", calor("alertas", "hora", "dia_semana", "cuboip_alarma"), "¿Cuándo se concentran las alertas?"),
    "al_camaras": ("cuboip_alertas_ia", "Cámaras con más alertas", barras("alertas", "camara", ["prioridad"], limit=10), None),
    "al_fp_analitica": ("cuboip_alertas_ia", "Precisión por analítica",
                        tabla(["analitica"], ["alertas", "precision_ia", "tasa_falsos", "mttr"], order="alertas",
                              conditional=[{"colorScheme": "#FF4D5E", "column": "tasa_falsos", "operator": ">", "targetValue": 0.3}]),
                        "Las analíticas con más falsos positivos son candidatas a recalibrar zona, horario o umbral."),
    "al_tiempos_dia": ("cuboip_alertas_ia", "Tiempos de atención y resolución", serie(["mtta", "mttr"], "fecha", kind="line", stack=False, fmt=",.1f"), None),
    "al_operadores": ("cuboip_alertas_ia", "Desempeño por operador", tabla(["resuelta_por"], ["alertas", "mttr", "p90_resolucion", "precision_ia"], order="alertas"), None),
    "al_sankey": ("cuboip_alertas_ia", "Flujo: categoría → prioridad", sankey("alertas", "categoria", "prioridad"), None),
    "al_ultimas": ("cuboip_alertas_ia", "Últimas alertas",
                   detalle(["fecha", "prioridad", "analitica", "camara", "estado", "calificacion", "resuelta_por", "min_resolucion"], "fecha",
                           formats={"min_resolucion": ",.1f"}), None),

    # --- Detecciones
    "det_total": ("cuboip_detecciones_hora", "Detecciones de IA", kpi_trend("detecciones", "hora_ts"), "Objetos detectados por el motor de visión."),
    "det_objetos": ("cuboip_detecciones_hora", "Objetos únicos seguidos", kpi("objetos", "tracks distintos"), None),
    "det_serie": ("cuboip_detecciones_hora", "Detecciones por hora y clase", serie(["detecciones"], "hora_ts", ["clase"], grain="PT1H", kind="area", xfmt="%d %b %H:%M"), None),
    "det_clase": ("cuboip_detecciones_hora", "Detecciones por clase", arbol("detecciones", ["clase"]), None),
    "det_camara": ("cuboip_detecciones_hora", "Actividad por cámara", barras("detecciones", "camara", limit=15), None),

    # --- Incidentes
    "in_total": ("cuboip_incidentes", "Folios", kpi_trend("folios", "fecha"), None),
    "in_abiertos": ("cuboip_incidentes", "Abiertos", kpi("folios_abiertos", "folios pendientes o en proceso"), None),
    "in_cierre": ("cuboip_incidentes", "Cerrados", kpi("tasa_cierre", "de los folios del periodo", ".0%"), None),
    "in_acept": ("cuboip_incidentes", "Aceptación (min)", kpi("prom_aceptacion", "promedio desde creación", ",.1f"), None),
    "in_llegada": ("cuboip_incidentes", "Llegada (min)", kpi("prom_llegada", "promedio al sitio", ",.1f"), None),
    "in_5min": ("cuboip_incidentes", "Llegada < 5 min", kpi("llegada_5min", "de los folios con llegada", ".0%"), None),
    "in_dia_origen": ("cuboip_incidentes", "Folios por día y origen", serie(["folios"], "fecha", ["origen"]), None),
    "in_origen": ("cuboip_incidentes", "Origen de los folios", dona("folios", "origen"), None),
    "in_situacion": ("cuboip_incidentes", "Situación", dona("folios", "situacion"), None),
    "in_top": ("cuboip_incidentes", "Incidencias más frecuentes", barras("folios", "incidencia", limit=10), None),
    "in_prio_estatus": ("cuboip_incidentes", "Estatus por prioridad", barras("folios", "estatus", ["prioridad"], horizontal=False), None),
    "in_corp": ("cuboip_despacho_corporacion", "Tiempos por corporación",
                tabla(["corporacion"], ["folios", "prom_aceptacion", "prom_llegada", "prom_cierre", "cumple_llegada"], order="folios"),
                "Un folio atendido por varias corporaciones cuenta en cada una."),
    "in_alarma_serie": ("cuboip_incidentes", "Alarmas y botones de pánico por día",
                        filtrado(serie(["folios"], "fecha", ["familia"]), SOLO_ALARMAS), None),
    "in_alarma_tabla": ("cuboip_incidentes", "Alarmas y botones por incidencia",
                        filtrado(tabla(["familia", "incidencia"], ["folios", "prom_aceptacion", "prom_llegada"], order="folios"),
                                 SOLO_ALARMAS), None),
    "in_tiempos": ("cuboip_incidentes", "Evolución de tiempos de atención",
                   serie(["prom_aceptacion", "prom_llegada", "prom_cierre"], "fecha", kind="line", stack=False, fmt=",.1f"), None),
    "in_calor": ("cuboip_incidentes", "Mapa de calor: día y hora", calor("folios", "hora", "dia_semana", "cuboip_alarma"), None),
    "in_mapa": ("cuboip_incidentes", "Mapa de incidentes", mapa(color=(255, 77, 94), radius=45), "Ubicación de cada folio con coordenadas."),
    "in_zona": ("cuboip_incidentes", "Folios por zona y colonia", arbol("folios", ["zona", "colonia"]), None),
    "in_flujo": ("cuboip_incidentes", "Flujo: origen → situación", sankey("folios", "origen", "situacion"), None),
    "in_ultimos": ("cuboip_incidentes", "Últimos folios",
                   detalle(["folio", "fecha", "incidencia", "origen", "prioridad", "estatus", "corporaciones", "min_llegada", "min_cierre"], "fecha",
                           formats={"min_llegada": ",.1f", "min_cierre": ",.1f", "folio": "d"}), None),

    # --- SLA por corporación
    "sla_acep": ("cuboip_despacho_corporacion", "Aceptación", kpi("cumple_aceptacion", "dentro de la meta", ".0%"), None),
    "sla_lleg": ("cuboip_despacho_corporacion", "Llegada", kpi("cumple_llegada", "dentro de la meta", ".0%"), None),
    "sla_cierre": ("cuboip_despacho_corporacion", "Cierre", kpi("cumple_cierre", "dentro de la meta", ".0%"), None),
    "sla_fuera": ("cuboip_despacho_corporacion", "Tarde al sitio", kpi("fuera_llegada", "llegadas fuera de meta"), None),
    "sla_corp_tabla": ("cuboip_despacho_corporacion", "Cumplimiento por corporación",
                       tabla(["corporacion"], ["despachos", "cumple_aceptacion", "cumple_llegada", "cumple_cierre", "p90_llegada"],
                             order="despachos"), None),
    "sla_corp_lleg": ("cuboip_despacho_corporacion", "Llegada contra meta por corporación",
                      barras("despachos", "corporacion", ["sla_llegada"]), None),
    "sla_prio_lleg": ("cuboip_despacho_corporacion", "Llegada contra meta por prioridad",
                      barras("despachos", "prioridad", ["sla_llegada"], horizontal=False), None),
    "sla_tendencia": ("cuboip_despacho_corporacion", "Cumplimiento por día",
                      serie(["cumple_aceptacion", "cumple_llegada", "cumple_cierre"], "fecha", kind="line", stack=False, fmt=".0%"), None),
    "sla_familia": ("cuboip_despacho_corporacion", "Cumplimiento en alarmas y botones",
                    filtrado(tabla(["familia", "corporacion"], ["despachos", "cumple_llegada", "prom_llegada"], order="despachos"), SOLO_ALARMAS), None),
    "sla_fuera_lista": ("cuboip_despacho_corporacion", "Atenciones fuera de meta",
                        filtrado(detalle(["folio", "fecha", "corporacion", "incidencia", "prioridad", "min_aceptacion", "min_llegada",
                                          "min_cierre", "sla_aceptacion", "sla_llegada", "sla_cierre"], "fecha",
                                         formats={"folio": "d", "min_aceptacion": ",.1f", "min_llegada": ",.1f", "min_cierre": ",.1f"}),
                                 FUERA_DE_META), "Folio y corporación con al menos un tramo fuera de la meta."),

    # --- Cámaras
    "cam_total": ("cuboip_camaras", "Cámaras", kpi("camaras", "en inventario"), None),
    "cam_disp": ("cuboip_camaras", "Video en línea", kpi("disponibilidad", "cámaras transmitiendo", ".0%"), "Cámaras en línea sobre el total."),
    "cam_disp_g": ("cuboip_camaras", "Disponibilidad de video", medidor("disponibilidad"), "Meta: 95 % o más de las cámaras en línea."),
    "cam_caidas": ("cuboip_camaras", "Sin conexión", kpi("camaras_caidas", "cámaras por revisar"), None),
    "cam_ia": ("cuboip_camaras", "Cobertura de IA", kpi("con_analitica", "con analítica activa", ".0%"), None),
    "cam_estado": ("cuboip_camaras", "Estado del video", dona("camaras", "estado_video"), None),
    "cam_corp": ("cuboip_camaras", "Cámaras por corporación y estado", barras("camaras", "corporacion", ["estado_video"]), None),
    "cam_mapa": ("cuboip_camaras", "Mapa de cámaras", mapa(color=(22, 163, 74), radius=18, dimension="estado_video"), None),
    "cam_marca": ("cuboip_camaras", "Marcas y modelos", arbol("camaras", ["marca", "modelo"]), None),
    "cam_detalle": ("cuboip_camaras", "Inventario y salud por cámara",
                    detalle(["camara", "corporacion", "estado_video", "horas_en_estado", "analiticas_activas", "alertas_7d",
                             "horas_grabadas_7d", "marca", "modelo", "vms"], "alertas_7d", page=20,
                            conditional=[{"colorScheme": "#DC2626", "column": "horas_en_estado", "operator": ">", "targetValue": 24}],
                            formats={"horas_en_estado": ",.1f", "horas_grabadas_7d": ",.1f"}),
                    "Las cámaras sin conexión por más de 24 h se resaltan."),
    "grab_horas": ("cuboip_grabaciones", "Horas grabadas por día", serie(["horas_video"], "inicio", ["camara"], fmt=",.0f"), None),
    "grab_gb": ("cuboip_grabaciones", "Almacenamiento consumido", kpi("gb_video", "GB grabados en el periodo", ",.1f"), None),

    # --- Vehículos
    "lpr_total": ("cuboip_placas", "Lecturas de placas", kpi_trend("lecturas", "fecha"), None),
    "lpr_unicas": ("cuboip_placas", "Placas únicas", kpi("placas_unicas", "vehículos distintos"), None),
    "lpr_hits": ("cuboip_placas", "Coincidencias en listas", kpi("hits_lista", "lista negra o de interés"), None),
    "lpr_conf": ("cuboip_placas", "Confianza de lectura", kpi("confianza_lpr", "promedio del lector", ".0%"), None),
    "lpr_serie": ("cuboip_placas", "Lecturas por día y lista", serie(["lecturas"], "fecha", ["lista"]), None),
    "lpr_marca": ("cuboip_placas", "Marcas más vistas", barras("lecturas", "marca", limit=10), None),
    "lpr_color": ("cuboip_placas", "Colores", dona("lecturas", "color", limit=10), None),
    "lpr_top": ("cuboip_placas", "Placas más recurrentes", tabla(["placa", "lista", "marca", "color"], ["lecturas"], limit=100), "Útil para detectar vehículos que merodean o visitantes frecuentes."),
    "lpr_calor": ("cuboip_placas", "Flujo vehicular: día y hora", calor("lecturas", "hora", "dia_semana"), None),
    "lpr_camara": ("cuboip_placas", "Lecturas por cámara", barras("lecturas", "camara", ["lista"]), None),
    "vel_exc": ("cuboip_velocidad", "Excesos de velocidad", kpi("excesos", "sobre el límite de la zona"), None),
    "vel_p85": ("cuboip_velocidad", "Velocidad P85", kpi("vel_p85", "km/h (criterio de diseño vial)", ",.1f"), None),
    "vel_serie": ("cuboip_velocidad", "Velocidad media y P85 por día", serie(["vel_media", "vel_p85"], "fecha", kind="line", stack=False, fmt=",.1f"), None),
    "vel_zona": ("cuboip_velocidad", "Mediciones por zona", barras("mediciones", "zona", ["resultado"]), None),
    "af_personas": ("cuboip_aforo", "Personas contadas", kpi("personas", "cruces de línea"), None),
    "af_vehiculos": ("cuboip_aforo", "Vehículos contados", kpi("vehiculos", "cruces de línea"), None),
    "af_serie": ("cuboip_aforo", "Aforo por hora", serie(["cruces"], "fecha", ["grupo"], grain="PT1H", kind="area", xfmt="%d %b %H:%M"), None),
    "af_clase": ("cuboip_aforo", "Aforo por clase y sentido", barras("cruces", "clase", ["sentido"]), None),
    "af_hora": ("cuboip_aforo", "Perfil horario del aforo", barras("cruces", "hora", ["grupo"], horizontal=False, sort_by_x=True), "Horas pico de personas y vehículos."),

    # --- Accesos
    "ac_total": ("cuboip_accesos", "Eventos de acceso", kpi_trend("accesos", "fecha"), None),
    "ac_den": ("cuboip_accesos", "Denegados", kpi("tasa_denegados", "del total de intentos", ".1%"), None),
    "ac_personas": ("cuboip_accesos", "Personas distintas", kpi("personas_unicas", "identificadas en puertas"), None),
    "ac_sincontacto": ("cuboip_accesos", "Sin contacto", kpi("sin_contacto", "rostro o código QR", ".0%"), None),
    "ac_serie": ("cuboip_accesos", "Accesos por día y resultado", serie(["accesos"], "fecha", ["resultado"]), None),
    "ac_metodo": ("cuboip_accesos", "Método de identificación", dona("accesos", "metodo"), None),
    "ac_perfil": ("cuboip_accesos", "Perfil de quien accede", dona("accesos", "perfil"), None),
    "ac_puerta": ("cuboip_accesos", "Uso por puerta", barras("accesos", "puerta", ["resultado"]), None),
    "ac_calor": ("cuboip_accesos", "Ocupación: día y hora", calor("accesos", "hora", "dia_semana"), "Cuándo entra y sale la gente del edificio."),
    "ac_depto": ("cuboip_accesos", "Accesos por departamento", barras("accesos", "departamento", limit=12), None),
    "ac_denegados": ("cuboip_accesos", "Intentos denegados y alertas",
                     tabla(["puerta", "persona", "metodo", "tipo"], ["denegados", "alertas_acceso"], order="denegados", limit=100), None),
    "vi_total": ("cuboip_visitas", "Visitas registradas", kpi("visitas", "en el periodo"), None),
    "vi_dentro": ("cuboip_visitas", "Dentro ahora", kpi("visitas_dentro", "visitantes en sitio"), None),
    "vi_estancia": ("cuboip_visitas", "Estancia (min)", kpi("estancia_media", "promedio por visita", ",.0f"), None),
    "vi_estado": ("cuboip_visitas", "Estado de las visitas", dona("visitas", "estado"), None),
    "vi_anfitrion": ("cuboip_visitas", "Anfitriones con más visitas", barras("visitas", "anfitrion", limit=10), None),
    "pq_pend": ("cuboip_paquetes", "Paquetes pendientes", kpi("paquetes_pendientes", "en recepción"), None),
    "pq_entrega": ("cuboip_paquetes", "Entrega (h)", kpi("horas_entrega", "promedio a entregar", ",.1f"), None),
    "pq_paqueteria": ("cuboip_paquetes", "Paquetes por paquetería", barras("paquetes", "paqueteria", ["estado"]), None),

    # --- Auditoría
    "au_total": ("cuboip_auditoria", "Acciones registradas", kpi_trend("acciones", "fecha"), None),
    "au_usuarios": ("cuboip_auditoria", "Usuarios activos", kpi("usuarios_activos", "en el periodo"), None),
    "au_fallidas": ("cuboip_auditoria", "Acciones fallidas", kpi("fallidas", "rechazadas o con error"), None),
    "au_export": ("cuboip_auditoria", "Exportaciones", kpi("exportaciones", "descargas de información"), "Seguimiento de salida de información (video, reportes, evidencia)."),
    "au_login_fail": ("cuboip_auditoria", "Sesiones fallidas", kpi("sesiones_fallidas", "intentos de acceso rechazados"), None),
    "au_serie": ("cuboip_auditoria", "Actividad por día y categoría", serie(["acciones"], "fecha", ["categoria"]), None),
    "au_usuario": ("cuboip_auditoria", "Actividad por usuario", barras("acciones", "usuario", ["categoria"]), None),
    "au_modulo": ("cuboip_auditoria", "Módulos más usados", arbol("acciones", ["modulo", "accion"]), None),
    "au_calor": ("cuboip_auditoria", "Uso: día y hora", calor("acciones", "hora", "dia_semana"), "Actividad fuera de horario laboral puede indicar accesos indebidos."),
    "au_resultado": ("cuboip_auditoria", "Resultado", dona("acciones", "resultado"), None),
    "au_detalle": ("cuboip_auditoria", "Bitácora reciente",
                   detalle(["fecha", "usuario", "categoria", "accion", "recurso", "resultado", "ip", "duracion_ms"], "fecha",
                           formats={"duracion_ms": ",d"}), None),
    "cp_preg": ("cuboip_copiloto", "Preguntas al copiloto", kpi("preguntas", "consultas en lenguaje natural"), None),
    "cp_conv": ("cuboip_copiloto", "Conversaciones", kpi("conversaciones", "sesiones con el copiloto"), None),
    "cp_resp": ("cuboip_copiloto", "Tiempo de respuesta", kpi("resp_seg", "segundos promedio", ",.1f"), None),

    # --- Tiempos de servicio y cumplimiento (khonsu.v_cumplimiento)
    "sv_total": ("cuboip_servicio", "Folios", kpi_trend("sv_folios", "fecha"), None),
    "sv_desp": ("cuboip_servicio", "Despacho (min)", kpi("prom_despacho", "recepción → primera unidad", ",.1f"), "Promedio desde que se recibe el folio hasta que se despacha la primera unidad."),
    "sv_lleg": ("cuboip_servicio", "Llegada (min)", kpi("prom_llegada_sv", "recepción → en sitio", ",.1f"), None),
    "sv_lleg90": ("cuboip_servicio", "Llegada P90 (min)", kpi("p90_llegada", "9 de cada 10 llegan antes", ",.1f"), None),
    "sv_cierre": ("cuboip_servicio", "Cierre (min)", kpi("prom_cierre_sv", "recepción → cierre", ",.1f"), None),
    "sv_meta": ("cuboip_servicio", "Cumplimiento de metas", kpi("pct_meta", "folios en meta / medidos", ".0%"), "Metas por tramo configuradas en CuboIP (Reportes → Tiempos de servicio → Metas)."),
    "sv_meta_g": ("cuboip_servicio", "Cumplimiento de metas", medidor("pct_meta", intervals="0.7,0.9,1", colors="1,4,2"), "Folios en meta sobre folios con meta y medición."),
    "sv_tramos": ("cuboip_servicio", "Tramos del servicio por incidencia",
                  barras_multi(["prom_atencion_sv", "prom_despacho", "prom_traslado", "prom_en_sitio"], "incidencia"),
                  "Minutos promedio de cada tramo: atención, despacho, traslado y tiempo en sitio."),
    "sv_tiempos": ("cuboip_servicio", "Evolución de los tiempos",
                   serie(["prom_despacho", "prom_llegada_sv", "p90_llegada", "prom_cierre_sv"], "fecha", kind="line", stack=False, fmt=",.1f"), None),
    "sv_meta_serie": ("cuboip_servicio", "Cumplimiento por día",
                      serie(["pct_meta", "pct_meta_despacho", "pct_meta_llegada", "pct_meta_cierre"], "fecha", kind="line", stack=False, fmt=".0%"), None),
    "sv_resultado": ("cuboip_servicio", "Resultado contra la meta", dona("sv_folios", "resultado_meta"), None),
    "sv_sitios": ("cuboip_servicio", "Ranking de sitios",
                  tabla(["sitio", "cliente"], ["sv_folios", "sv_abiertos", "prom_llegada_sv", "p90_llegada", "prom_cierre_sv", "pct_meta"],
                        order="sv_folios", limit=200,
                        conditional=[{"colorScheme": "#DC2626", "column": "pct_meta", "operator": "<", "targetValue": 0.8}],
                        formats={"prom_llegada_sv": ",.1f", "p90_llegada": ",.1f", "prom_cierre_sv": ",.1f", "pct_meta": ".0%"}),
                  "Sitios con más folios; en rojo los que cumplen menos del 80 % de sus metas."),
    "sv_lentos": ("cuboip_servicio", "Sitios con llegada más lenta (P90)", barras("p90_llegada", "sitio", limit=10, fmt=",.1f"), None),
    "sv_clientes": ("cuboip_servicio", "Clientes",
                    tabla(["cliente"], ["sv_folios", "sv_sitios", "prom_llegada_sv", "pct_meta", "sv_fuera_meta"], order="sv_folios",
                          formats={"prom_llegada_sv": ",.1f", "pct_meta": ".0%"}), None),
    "sv_incid": ("cuboip_servicio", "Tiempos y cumplimiento por incidencia",
                 tabla(["incidencia"], ["sv_folios", "prom_despacho", "prom_llegada_sv", "prom_cierre_sv", "pct_meta"], order="sv_folios",
                       formats={"prom_despacho": ",.1f", "prom_llegada_sv": ",.1f", "prom_cierre_sv": ",.1f", "pct_meta": ".0%"}), None),
    "sv_corp": ("cuboip_servicio", "Cumplimiento por corporación", barras("pct_meta", "corporacion", fmt=".0%"), None),
    "sv_calor": ("cuboip_servicio", "Mapa de calor: día y hora", calor("sv_folios", "hora", "dia_semana", "cuboip_alarma"), "Cuándo se concentran los folios."),
    "sv_calor_lleg": ("cuboip_servicio", "Llegada promedio: día y hora", calor("prom_llegada_sv", "hora", "dia_semana", "cuboip_alarma", ",.1f"), "Franjas en que se llega más tarde."),
    "sv_mapa": ("cuboip_calor", "Mapa de calor de folios", mapa_calor("calor_peso"), "Densidad de folios ponderada por prioridad (urgente 4, alta 3, media 2, baja 1)."),
    "sv_proto": ("cuboip_servicio", "Protocolos cumplidos", kpi("pct_protocolo", "de los folios con protocolo evaluado", ".0%"), None),
    "sv_proto_pasos": ("cuboip_servicio", "Pasos cumplidos", kpi("pct_pasos", "pasos hechos / pasos del protocolo", ".0%"), None),
    "sv_proto_res": ("cuboip_servicio", "Resultado del protocolo", dona("sv_folios", "resultado_protocolo"), None),
    "sv_detalle": ("cuboip_servicio", "Folios fuera de meta",
                   detalle(["folio", "fecha", "sitio", "cliente", "incidencia", "prioridad", "meta", "min_despacho", "min_llegada", "min_cierre",
                            "resultado_meta"], "fecha",
                           formats={"folio": "d", "min_despacho": ",.1f", "min_llegada": ",.1f", "min_cierre": ",.1f"}),
                   "Últimos folios con su meta; filtra Resultado de la meta = Fuera de meta para revisar."),

}


def _md(titulo, texto=""):
    return f"### {titulo}\n{texto}" if texto else f"### {titulo}"


def _metas_md():
    filas = "\n".join(f"| {p} | {a} | {l} | {c} |" for p, (a, l, c) in METAS_SLA.items())
    return ("### Metas de atención (provisionales)\n"
            "Minutos desde que se crea el folio. Cada corporación despachada se evalúa por separado.\n\n"
            "| Prioridad | Aceptación | Llegada | Cierre |\n|---|---|---|---|\n" + filas)


DASHBOARDS = [
    {
        "slug": "resumen-ejecutivo",
        "title": "Resumen ejecutivo",
        "description": "Vista de mando: alertas de IA, incidentes, cámaras y accesos en un solo lugar.",
        "filters": [("time", "Periodo", "Last month"), ("select", "Corporación", "corporacion", "cuboip_alertas_ia")],
        "rows": [
            [("md", 12, 12, "## Centro de mando CuboIP\nPanorama del periodo seleccionado. Los indicadores se actualizan cada 10 minutos. Cambia el periodo o la corporación en el panel de filtros.")],
            [("al_total", 3, 30), ("in_total", 3, 30), ("det_total", 3, 30), ("ac_total", 3, 30)],
            [("al_pend", 2, 22), ("al_mttr", 2, 22), ("al_prec", 2, 22), ("in_abiertos", 2, 22), ("in_llegada", 2, 22), ("cam_disp", 2, 22)],
            [("al_dia_prio", 8, 50), ("al_categoria", 4, 50)],
            [("in_dia_origen", 8, 50), ("in_situacion", 4, 50)],
            [("al_calor", 6, 50), ("in_mapa", 6, 50)],
            [("al_camaras", 6, 50), ("in_top", 6, 50)],
        ],
    },
    {
        "slug": "alertas-ia",
        "title": "Alertas de IA y analíticas de video",
        "description": "Volumen, precisión y tiempos de atención de las analíticas de video.",
        "filters": [("time", "Periodo", "Last month"), ("select", "Prioridad", "prioridad", "cuboip_alertas_ia"),
                    ("select", "Categoría", "categoria", "cuboip_alertas_ia"), ("select", "Cámara", "camara", "cuboip_alertas_ia")],
        "rows": [
            [("al_total", 3, 30), ("al_crit", 3, 30), ("al_mtta", 2, 30), ("al_mttr", 2, 30), ("al_prec", 2, 30)],
            [("al_hora_prio", 12, 50)],
            [("al_analitica", 6, 55), ("al_sankey", 6, 55)],
            [("md", 12, 10, _md("Calidad de la IA", "Las calificaciones de los operadores (confirmada / falso positivo) miden la precisión real de cada analítica."))],
            [("al_calif", 4, 50), ("al_fp_analitica", 8, 50)],
            [("al_tiempos_dia", 6, 50), ("al_operadores", 6, 50)],
            [("al_calor", 6, 50), ("al_estado", 3, 50), ("al_escal", 3, 50)],
            [("md", 12, 10, _md("Actividad del motor de visión", "Detecciones de objetos por hora, incluso las que no generan alerta."))],
            [("det_total", 3, 30), ("det_objetos", 3, 30), ("det_clase", 6, 50)],
            [("det_serie", 8, 50), ("det_camara", 4, 50)],
            [("al_ultimas", 12, 60)],
        ],
    },
    {
        "slug": "incidentes",
        "title": "Incidentes y despacho",
        "description": "Folios del centro de mando: origen, estatus, tiempos de atención y ubicación.",
        "filters": [("time", "Periodo", "Last month"), ("select", "Origen", "origen", "cuboip_incidentes"),
                    ("select", "Prioridad", "prioridad", "cuboip_incidentes"), ("select", "Familia", "familia", "cuboip_incidentes"),
                    ("select", "Incidencia", "incidencia", "cuboip_incidentes")],
        "rows": [
            [("in_total", 2, 30), ("in_abiertos", 2, 30), ("in_cierre", 2, 30), ("in_acept", 2, 30), ("in_llegada", 2, 30), ("in_5min", 2, 30)],
            [("in_dia_origen", 8, 50), ("in_origen", 4, 50)],
            [("in_mapa", 7, 70), ("in_top", 5, 70)],
            [("in_prio_estatus", 6, 50), ("in_flujo", 6, 50)],
            [("md", 12, 10, _md("Tiempos de atención", "Minutos desde la creación del folio hasta aceptación, llegada al sitio y cierre. Se descartan valores atípicos (más de 24 h)."))],
            [("in_tiempos", 7, 50), ("in_corp", 5, 50)],
            [("md", 12, 10, _md("Alarmas y botones de pánico", "Incidencias agrupadas por familia según su nombre; incluye las alarmas que entran por el 911."))],
            [("in_alarma_serie", 7, 50), ("in_alarma_tabla", 5, 50)],
            [("in_calor", 6, 50), ("in_zona", 6, 50)],
            [("in_ultimos", 12, 60)],
        ],
    },
    {
        "slug": "sla-corporaciones",
        "title": "SLA de despacho por corporación",
        "description": "Cumplimiento de las metas de aceptación, llegada y cierre de cada corporación despachada.",
        "filters": [("time", "Periodo", "Last month"), ("select", "Corporación", "corporacion", "cuboip_despacho_corporacion"),
                    ("select", "Prioridad", "prioridad", "cuboip_despacho_corporacion"),
                    ("select", "Familia", "familia", "cuboip_despacho_corporacion"),
                    ("select", "Incidencia", "incidencia", "cuboip_despacho_corporacion")],
        "rows": [
            [("sla_acep", 3, 26), ("sla_lleg", 3, 26), ("sla_cierre", 3, 26), ("sla_fuera", 3, 26)],
            [("md", 4, 40, _metas_md()), ("sla_corp_tabla", 8, 40)],
            [("sla_corp_lleg", 6, 50), ("sla_prio_lleg", 6, 50)],
            [("sla_tendencia", 7, 50), ("sla_familia", 5, 50)],
            [("sla_fuera_lista", 12, 60)],
        ],
    },
    {
        "slug": "camaras",
        "title": "Cámaras y video",
        "description": "Salud del parque de cámaras, cobertura de IA y grabación.",
        "filters": [("select", "Corporación", "corporacion", "cuboip_camaras"), ("select", "Estado de video", "estado_video", "cuboip_camaras"),
                    ("time", "Periodo de grabación", "Last week")],
        "rows": [
            [("cam_total", 3, 26), ("cam_disp", 3, 26), ("cam_caidas", 3, 26), ("cam_ia", 3, 26)],
            [("cam_mapa", 6, 65), ("cam_disp_g", 3, 65), ("cam_estado", 3, 65)],
            [("cam_corp", 6, 50), ("cam_marca", 6, 50)],
            [("cam_detalle", 12, 60)],
            [("md", 12, 10, _md("Grabación", "Horas de video y almacenamiento del grabador de CuboIP."))],
            [("grab_horas", 9, 50), ("grab_gb", 3, 50)],
        ],
    },
    {
        "slug": "vehiculos",
        "title": "Vehículos, placas y aforo",
        "description": "Lectura de placas, listas de vigilancia, velocidad y conteo de personas y vehículos.",
        "filters": [("time", "Periodo", "Last month"), ("select", "Cámara", "camara", "cuboip_placas"), ("select", "Lista", "lista", "cuboip_placas")],
        "rows": [
            [("lpr_total", 3, 30), ("lpr_unicas", 3, 30), ("lpr_hits", 3, 30), ("lpr_conf", 3, 30)],
            [("lpr_serie", 8, 50), ("lpr_color", 4, 50)],
            [("lpr_marca", 4, 55), ("lpr_calor", 4, 55), ("lpr_top", 4, 55)],
            [("lpr_camara", 12, 45)],
            [("md", 12, 10, _md("Velocidad", "Mediciones de las zonas con analítica de velocidad."))],
            [("vel_exc", 3, 26), ("vel_p85", 3, 26), ("vel_serie", 6, 50)],
            [("vel_zona", 12, 40)],
            [("md", 12, 10, _md("Aforo", "Cruces de las líneas de conteo configuradas en las cámaras."))],
            [("af_personas", 3, 26), ("af_vehiculos", 3, 26), ("af_clase", 6, 50)],
            [("af_serie", 7, 50), ("af_hora", 5, 50)],
        ],
    },
    {
        "slug": "accesos-corporativo",
        "title": "Control de acceso y corporativo",
        "description": "Puertas, identificaciones, visitantes y paquetería del corporativo.",
        "filters": [("time", "Periodo", "Last month"), ("select", "Puerta", "puerta", "cuboip_accesos"),
                    ("select", "Método", "metodo", "cuboip_accesos"), ("select", "Corporación", "corporacion", "cuboip_accesos")],
        "rows": [
            [("ac_total", 3, 30), ("ac_den", 3, 30), ("ac_personas", 3, 30), ("ac_sincontacto", 3, 30)],
            [("ac_serie", 8, 50), ("ac_metodo", 4, 50)],
            [("ac_calor", 6, 50), ("ac_puerta", 6, 50)],
            [("ac_perfil", 4, 50), ("ac_depto", 4, 50), ("ac_denegados", 4, 50)],
            [("md", 12, 10, _md("Visitantes y paquetería"))],
            [("vi_total", 2, 26), ("vi_dentro", 2, 26), ("vi_estancia", 2, 26), ("pq_pend", 3, 26), ("pq_entrega", 3, 26)],
            [("vi_estado", 4, 50), ("vi_anfitrion", 4, 50), ("pq_paqueteria", 4, 50)],
        ],
    },
    {
        "slug": "auditoria",
        "title": "Auditoría y uso de la plataforma",
        "description": "Quién hace qué en CuboIP: acciones, exportaciones, sesiones y copiloto.",
        "filters": [("time", "Periodo", "Last month"), ("select", "Usuario", "usuario", "cuboip_auditoria"),
                    ("select", "Categoría", "categoria", "cuboip_auditoria")],
        "rows": [
            [("au_total", 3, 30), ("au_usuarios", 2, 30), ("au_fallidas", 2, 30), ("au_export", 2, 30), ("au_login_fail", 3, 30)],
            [("au_serie", 8, 50), ("au_resultado", 4, 50)],
            [("au_usuario", 6, 55), ("au_modulo", 6, 55)],
            [("au_calor", 6, 50), ("cp_preg", 2, 50), ("cp_conv", 2, 50), ("cp_resp", 2, 50)],
            [("au_detalle", 12, 60)],
        ],
    },
    {
        "slug": "servicio",
        "title": "Tiempos de servicio y cumplimiento",
        "description": "Recepción → despacho → llegada → cierre, metas por tramo, protocolos, ranking de sitios y mapas de calor.",
        "filters": [("time", "Periodo", "Last month"), ("select", "Cliente", "cliente", "cuboip_servicio"),
                    ("select", "Sitio", "sitio", "cuboip_servicio"), ("select", "Corporación", "corporacion", "cuboip_servicio"),
                    ("select", "Incidencia", "incidencia", "cuboip_servicio"), ("select", "Prioridad", "prioridad", "cuboip_servicio"),
                    ("select", "Resultado de la meta", "resultado_meta", "cuboip_servicio")],
        "rows": [
            [("md", 12, 10, _md("Tiempos de servicio", "Minutos desde que se recibe el folio. Sin simulaciones; los tramos atípicos se descartan. "
                                 "Las metas se configuran en CuboIP: Reportes → Tiempos de servicio → Metas."))],
            [("sv_total", 3, 30), ("sv_desp", 2, 30), ("sv_lleg", 2, 30), ("sv_lleg90", 2, 30), ("sv_cierre", 3, 30)],
            [("sv_tiempos", 8, 50), ("sv_meta_g", 4, 50)],
            [("sv_tramos", 6, 55), ("sv_incid", 6, 55)],
            [("md", 12, 10, _md("Cumplimiento", "Cada tramo se compara con la meta más específica que lo define (sitio, cliente, incidencia, prioridad o corporación)."))],
            [("sv_meta", 3, 50), ("sv_meta_serie", 6, 50), ("sv_resultado", 3, 50)],
            [("sv_proto", 3, 40), ("sv_proto_pasos", 3, 40), ("sv_proto_res", 3, 40),
             ("md", 3, 40, "#### Protocolos\nSe llenan cuando el módulo de protocolos guiados registra los pasos de cada folio. Mientras tanto se ven como *Sin protocolo*.")],
            [("md", 12, 10, _md("Sitios y clientes"))],
            [("sv_sitios", 8, 60), ("sv_lentos", 4, 60)],
            [("sv_clientes", 6, 50), ("sv_corp", 6, 50)],
            [("md", 12, 10, _md("Mapas de calor"))],
            [("sv_mapa", 7, 70), ("sv_calor", 5, 70)],
            [("sv_calor_lleg", 12, 50)],
            [("sv_detalle", 12, 60)],
        ],
    },
]
