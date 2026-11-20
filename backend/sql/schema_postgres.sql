-- PostgreSQL database dump


-- Dumped from database version 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)

-- Name: alerta; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.alerta (
    id integer NOT NULL,
    lote_id integer NOT NULL,
    ts timestamp without time zone NOT NULL,
    tipo character varying(24) NOT NULL,
    severidad character varying(8) NOT NULL,
    contaminante character varying(8),
    valor double precision,
    umbral double precision,
    mensaje text NOT NULL
);

-- Name: alerta_id_seq; Type: SEQUENCE; Schema: public; Owner: -

CREATE SEQUENCE public.alerta_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: alerta_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -

ALTER SEQUENCE public.alerta_id_seq OWNED BY public.alerta.id;

-- Name: filtro; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.filtro (
    id integer NOT NULL,
    codigo character varying(24) NOT NULL,
    nombre character varying(80) NOT NULL,
    tecnologia character varying(80) NOT NULL,
    descripcion text NOT NULL,
    eta_pm25 double precision NOT NULL,
    eta_pm10 double precision NOT NULL,
    eta_co2 double precision NOT NULL,
    eta_co double precision NOT NULL,
    eta_tvoc double precision NOT NULL
);

-- Name: filtro_id_seq; Type: SEQUENCE; Schema: public; Owner: -

CREATE SEQUENCE public.filtro_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: filtro_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -

ALTER SEQUENCE public.filtro_id_seq OWNED BY public.filtro.id;

-- Name: lote; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.lote (
    id integer NOT NULL,
    codigo character varying(24) NOT NULL,
    escenario character varying(32) NOT NULL,
    estado character varying(10) NOT NULL,
    ingreso_ts timestamp without time zone NOT NULL,
    fin_ts timestamp without time zone,
    duracion_min double precision NOT NULL,
    volumen_m3 double precision NOT NULL,
    caudal_m3h double precision NOT NULL,
    firma_tren character varying(120) NOT NULL,
    isr_entrada double precision,
    isr_salida double precision,
    nivel_entrada character varying(12),
    nivel_salida character varying(12),
    clasificacion character varying(16),
    reduccion_global double precision,
    t_meta_min double precision,
    t_meta_pred_min double precision,
    CONSTRAINT ck_lote_estado CHECK (((estado)::text = ANY ((ARRAY['abierto'::character varying, 'cerrado'::character varying])::text[])))
);

-- Name: lote_filtro; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.lote_filtro (
    lote_id integer NOT NULL,
    filtro_id integer NOT NULL,
    orden integer NOT NULL
);

-- Name: lote_id_seq; Type: SEQUENCE; Schema: public; Owner: -

CREATE SEQUENCE public.lote_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: lote_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -

ALTER SEQUENCE public.lote_id_seq OWNED BY public.lote.id;

-- Name: medicion; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.medicion (
    id integer NOT NULL,
    lote_id integer NOT NULL,
    etapa character varying(8) NOT NULL,
    ts timestamp without time zone NOT NULL,
    t_seg double precision NOT NULL,
    pm25 double precision NOT NULL,
    pm10 double precision NOT NULL,
    co2 double precision NOT NULL,
    co double precision NOT NULL,
    tvoc double precision NOT NULL,
    CONSTRAINT ck_medicion_etapa CHECK (((etapa)::text = ANY ((ARRAY['entrada'::character varying, 'proceso'::character varying, 'salida'::character varying])::text[])))
);

-- Name: medicion_id_seq; Type: SEQUENCE; Schema: public; Owner: -

CREATE SEQUENCE public.medicion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: medicion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -

ALTER SEQUENCE public.medicion_id_seq OWNED BY public.medicion.id;

-- Name: tasa_decaimiento; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.tasa_decaimiento (
    lote_id integer NOT NULL,
    contaminante character varying(8) NOT NULL,
    k_h double precision NOT NULL,
    r2 double precision NOT NULL,
    n_puntos integer NOT NULL
);

-- Name: vw_eficiencia_lote; Type: VIEW; Schema: public; Owner: -

CREATE VIEW public.vw_eficiencia_lote AS
 SELECT l.id AS lote_id,
    l.codigo,
    l.escenario,
    l.ingreso_ts,
    l.firma_tren,
    l.duracion_min,
    avg(
        CASE
            WHEN ((m.etapa)::text = 'entrada'::text) THEN m.pm25
            ELSE NULL::double precision
        END) AS pm25_entrada,
    avg(
        CASE
            WHEN ((m.etapa)::text = 'salida'::text) THEN m.pm25
            ELSE NULL::double precision
        END) AS pm25_salida,
    avg(
        CASE
            WHEN ((m.etapa)::text = 'entrada'::text) THEN m.pm10
            ELSE NULL::double precision
        END) AS pm10_entrada,
    avg(
        CASE
            WHEN ((m.etapa)::text = 'salida'::text) THEN m.pm10
            ELSE NULL::double precision
        END) AS pm10_salida,
    avg(
        CASE
            WHEN ((m.etapa)::text = 'entrada'::text) THEN m.co2
            ELSE NULL::double precision
        END) AS co2_entrada,
    avg(
        CASE
            WHEN ((m.etapa)::text = 'salida'::text) THEN m.co2
            ELSE NULL::double precision
        END) AS co2_salida,
    avg(
        CASE
            WHEN ((m.etapa)::text = 'entrada'::text) THEN m.co
            ELSE NULL::double precision
        END) AS co_entrada,
    avg(
        CASE
            WHEN ((m.etapa)::text = 'salida'::text) THEN m.co
            ELSE NULL::double precision
        END) AS co_salida
   FROM (public.lote l
     JOIN public.medicion m ON ((m.lote_id = l.id)))
  WHERE ((l.estado)::text = 'cerrado'::text)
  GROUP BY l.id, l.codigo, l.escenario, l.ingreso_ts, l.firma_tren, l.duracion_min;

-- Name: alerta id; Type: DEFAULT; Schema: public; Owner: -

ALTER TABLE ONLY public.alerta ALTER COLUMN id SET DEFAULT nextval('public.alerta_id_seq'::regclass);

-- Name: filtro id; Type: DEFAULT; Schema: public; Owner: -

ALTER TABLE ONLY public.filtro ALTER COLUMN id SET DEFAULT nextval('public.filtro_id_seq'::regclass);

-- Name: lote id; Type: DEFAULT; Schema: public; Owner: -

ALTER TABLE ONLY public.lote ALTER COLUMN id SET DEFAULT nextval('public.lote_id_seq'::regclass);

-- Name: medicion id; Type: DEFAULT; Schema: public; Owner: -

ALTER TABLE ONLY public.medicion ALTER COLUMN id SET DEFAULT nextval('public.medicion_id_seq'::regclass);

-- Name: alerta alerta_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.alerta
    ADD CONSTRAINT alerta_pkey PRIMARY KEY (id);

-- Name: filtro filtro_codigo_key; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.filtro
    ADD CONSTRAINT filtro_codigo_key UNIQUE (codigo);

-- Name: filtro filtro_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.filtro
    ADD CONSTRAINT filtro_pkey PRIMARY KEY (id);

-- Name: lote lote_codigo_key; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.lote
    ADD CONSTRAINT lote_codigo_key UNIQUE (codigo);

-- Name: lote_filtro lote_filtro_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.lote_filtro
    ADD CONSTRAINT lote_filtro_pkey PRIMARY KEY (lote_id, filtro_id);

-- Name: lote lote_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.lote
    ADD CONSTRAINT lote_pkey PRIMARY KEY (id);

-- Name: medicion medicion_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.medicion
    ADD CONSTRAINT medicion_pkey PRIMARY KEY (id);

-- Name: tasa_decaimiento tasa_decaimiento_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.tasa_decaimiento
    ADD CONSTRAINT tasa_decaimiento_pkey PRIMARY KEY (lote_id, contaminante);

-- Name: ix_alerta_ts; Type: INDEX; Schema: public; Owner: -

CREATE INDEX ix_alerta_ts ON public.alerta USING btree (ts);

-- Name: ix_lote_ingreso; Type: INDEX; Schema: public; Owner: -

CREATE INDEX ix_lote_ingreso ON public.lote USING btree (ingreso_ts);

-- Name: ix_medicion_lote_etapa; Type: INDEX; Schema: public; Owner: -

CREATE INDEX ix_medicion_lote_etapa ON public.medicion USING btree (lote_id, etapa);

-- Name: alerta alerta_lote_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.alerta
    ADD CONSTRAINT alerta_lote_id_fkey FOREIGN KEY (lote_id) REFERENCES public.lote(id) ON DELETE CASCADE;

-- Name: lote_filtro lote_filtro_filtro_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.lote_filtro
    ADD CONSTRAINT lote_filtro_filtro_id_fkey FOREIGN KEY (filtro_id) REFERENCES public.filtro(id);

-- Name: lote_filtro lote_filtro_lote_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.lote_filtro
    ADD CONSTRAINT lote_filtro_lote_id_fkey FOREIGN KEY (lote_id) REFERENCES public.lote(id) ON DELETE CASCADE;

-- Name: medicion medicion_lote_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.medicion
    ADD CONSTRAINT medicion_lote_id_fkey FOREIGN KEY (lote_id) REFERENCES public.lote(id) ON DELETE CASCADE;

-- Name: tasa_decaimiento tasa_decaimiento_lote_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.tasa_decaimiento
    ADD CONSTRAINT tasa_decaimiento_lote_id_fkey FOREIGN KEY (lote_id) REFERENCES public.lote(id) ON DELETE CASCADE;

-- PostgreSQL database dump complete


