-- Complemento de amon/docs/reportes/crear-usuario-lectura.sql para el rol de Superset:
-- el script oficial solo cubre public; aquí se da lectura a vision y corp sin datos sensibles.
\set ON_ERROR_STOP on
BEGIN;
ALTER ROLE superset_ro CONNECTION LIMIT 20;  -- 4x4 hilos web + 4 del worker
ALTER ROLE superset_ro SET statement_timeout = '60s';
ALTER ROLE superset_ro SET search_path = vision, corp, public;
GRANT USAGE ON SCHEMA vision, corp TO superset_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA vision, corp TO superset_ro;
-- Las tablas nuevas NO se exponen solas (igual que el script oficial): se re-ejecuta tras migraciones.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public, vision, corp REVOKE SELECT ON TABLES FROM superset_ro;

REVOKE ALL ON vision.face_embeddings FROM superset_ro;          -- biometría
DO $$
DECLARE t record; cols text;
BEGIN
  FOR t IN SELECT * FROM (VALUES
      ('vision','cameras',   ARRAY['rtsp_url','live_url']),
      ('vision','events',    ARRAY['embedding','reid_embedding']),
      ('vision','persons',   ARRAY['embedding']),
      ('corp','empleados',   ARRAY['curp','rfc','telefono_emergencia','contacto_emergencia']),
      ('corp','visitas',     ARRAY['identificacion_numero','identificacion_foto','firma','qr_hash','qr_codigo']),
      ('corp','paquetes',    ARRAY['entrega_hash','entrega_codigo','firma']),
      ('corp','credenciales',ARRAY['numero','pin'])
    ) AS s(esq, tabla, excluir)
  LOOP
    IF to_regclass(format('%I.%I', t.esq, t.tabla)) IS NOT NULL THEN
      EXECUTE format('REVOKE ALL ON TABLE %I.%I FROM superset_ro', t.esq, t.tabla);
      SELECT string_agg(quote_ident(column_name), ', ' ORDER BY ordinal_position) INTO cols
        FROM information_schema.columns
       WHERE table_schema = t.esq AND table_name = t.tabla AND NOT (column_name = ANY (t.excluir));
      EXECUTE format('GRANT SELECT (%s) ON TABLE %I.%I TO superset_ro', cols, t.esq, t.tabla);
    END IF;
  END LOOP;
END $$;
COMMIT;
