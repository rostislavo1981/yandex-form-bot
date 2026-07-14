--
-- PostgreSQL database dump
--

\restrict 2qTZ5vb9fHGLog1fKbxhThdcfwi4fntrHo0lbqIHQfXtbsvCLUzBhY8dqpwV8cE

-- Dumped from database version 16.14
-- Dumped by pg_dump version 16.14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


--
-- Name: assignment_schedule_type; Type: TYPE; Schema: public; Owner: mdr_user
--

CREATE TYPE public.assignment_schedule_type AS ENUM (
    'daily',
    'weekdays'
);


ALTER TYPE public.assignment_schedule_type OWNER TO mdr_user;

--
-- Name: catalog_import_status; Type: TYPE; Schema: public; Owner: mdr_user
--

CREATE TYPE public.catalog_import_status AS ENUM (
    'uploaded',
    'validated',
    'applied',
    'failed'
);


ALTER TYPE public.catalog_import_status OWNER TO mdr_user;

--
-- Name: daily_report_status; Type: TYPE; Schema: public; Owner: mdr_user
--

CREATE TYPE public.daily_report_status AS ENUM (
    'submitted'
);


ALTER TYPE public.daily_report_status OWNER TO mdr_user;

--
-- Name: equipment_ownership; Type: TYPE; Schema: public; Owner: mdr_user
--

CREATE TYPE public.equipment_ownership AS ENUM (
    'own',
    'rented',
    'contractor'
);


ALTER TYPE public.equipment_ownership OWNER TO mdr_user;

--
-- Name: notification_status; Type: TYPE; Schema: public; Owner: mdr_user
--

CREATE TYPE public.notification_status AS ENUM (
    'pending',
    'sent',
    'failed'
);


ALTER TYPE public.notification_status OWNER TO mdr_user;

--
-- Name: object_execution_method; Type: TYPE; Schema: public; Owner: mdr_user
--

CREATE TYPE public.object_execution_method AS ENUM (
    'own',
    'contractor'
);


ALTER TYPE public.object_execution_method OWNER TO mdr_user;

--
-- Name: outbox_event_kind; Type: TYPE; Schema: public; Owner: mdr_user
--

CREATE TYPE public.outbox_event_kind AS ENUM (
    'report_submitted',
    'control_panel_refresh'
);


ALTER TYPE public.outbox_event_kind OWNER TO mdr_user;

--
-- Name: outbox_event_status; Type: TYPE; Schema: public; Owner: mdr_user
--

CREATE TYPE public.outbox_event_status AS ENUM (
    'pending',
    'processing',
    'done',
    'failed'
);


ALTER TYPE public.outbox_event_status OWNER TO mdr_user;

--
-- Name: report_obligation_status; Type: TYPE; Schema: public; Owner: mdr_user
--

CREATE TYPE public.report_obligation_status AS ENUM (
    'pending',
    'submitted',
    'late',
    'missed',
    'exempt'
);


ALTER TYPE public.report_obligation_status OWNER TO mdr_user;

--
-- Name: user_role; Type: TYPE; Schema: public; Owner: mdr_user
--

CREATE TYPE public.user_role AS ENUM (
    'responsible',
    'manager',
    'admin'
);


ALTER TYPE public.user_role OWNER TO mdr_user;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: mdr_user
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO mdr_user;

--
-- Name: catalog_imports; Type: TABLE; Schema: public; Owner: mdr_user
--

CREATE TABLE public.catalog_imports (
    id bigint NOT NULL,
    filename character varying(255) NOT NULL,
    status public.catalog_import_status NOT NULL,
    summary_json jsonb,
    errors_json jsonb,
    created_by character varying(64),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    applied_at timestamp with time zone
);


ALTER TABLE public.catalog_imports OWNER TO mdr_user;

--
-- Name: catalog_imports_id_seq; Type: SEQUENCE; Schema: public; Owner: mdr_user
--

CREATE SEQUENCE public.catalog_imports_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.catalog_imports_id_seq OWNER TO mdr_user;

--
-- Name: catalog_imports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mdr_user
--

ALTER SEQUENCE public.catalog_imports_id_seq OWNED BY public.catalog_imports.id;


--
-- Name: contractors; Type: TABLE; Schema: public; Owner: mdr_user
--

CREATE TABLE public.contractors (
    id bigint NOT NULL,
    code character varying(64) NOT NULL,
    name character varying(255) NOT NULL,
    search_aliases text,
    active boolean NOT NULL,
    sort_order bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.contractors OWNER TO mdr_user;

--
-- Name: contractors_id_seq; Type: SEQUENCE; Schema: public; Owner: mdr_user
--

CREATE SEQUENCE public.contractors_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.contractors_id_seq OWNER TO mdr_user;

--
-- Name: contractors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mdr_user
--

ALTER SEQUENCE public.contractors_id_seq OWNED BY public.contractors.id;


--
-- Name: daily_reports; Type: TABLE; Schema: public; Owner: mdr_user
--

CREATE TABLE public.daily_reports (
    id bigint NOT NULL,
    report_date date NOT NULL,
    responsible_user_id bigint NOT NULL,
    object_id bigint NOT NULL,
    stage_id bigint NOT NULL,
    contractor_id bigint,
    comment text,
    staff_itr bigint NOT NULL,
    staff_internal bigint NOT NULL,
    staff_external bigint NOT NULL,
    soil_export_m3 numeric(14,2),
    status public.daily_report_status NOT NULL,
    idempotency_key character varying(64) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.daily_reports OWNER TO mdr_user;

--
-- Name: daily_reports_id_seq; Type: SEQUENCE; Schema: public; Owner: mdr_user
--

CREATE SEQUENCE public.daily_reports_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.daily_reports_id_seq OWNER TO mdr_user;

--
-- Name: daily_reports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mdr_user
--

ALTER SEQUENCE public.daily_reports_id_seq OWNED BY public.daily_reports.id;


--
-- Name: equipment_types; Type: TABLE; Schema: public; Owner: mdr_user
--

CREATE TABLE public.equipment_types (
    default_unit_id bigint,
    id bigint NOT NULL,
    code character varying(64) NOT NULL,
    name character varying(255) NOT NULL,
    search_aliases text,
    active boolean NOT NULL,
    sort_order bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.equipment_types OWNER TO mdr_user;

--
-- Name: equipment_types_id_seq; Type: SEQUENCE; Schema: public; Owner: mdr_user
--

CREATE SEQUENCE public.equipment_types_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.equipment_types_id_seq OWNER TO mdr_user;

--
-- Name: equipment_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mdr_user
--

ALTER SEQUENCE public.equipment_types_id_seq OWNED BY public.equipment_types.id;


--
-- Name: group_members; Type: TABLE; Schema: public; Owner: mdr_user
--

CREATE TABLE public.group_members (
    id bigint NOT NULL,
    group_id bigint NOT NULL,
    user_id bigint NOT NULL,
    active boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.group_members OWNER TO mdr_user;

--
-- Name: group_members_id_seq; Type: SEQUENCE; Schema: public; Owner: mdr_user
--

CREATE SEQUENCE public.group_members_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.group_members_id_seq OWNER TO mdr_user;

--
-- Name: group_members_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mdr_user
--

ALTER SEQUENCE public.group_members_id_seq OWNED BY public.group_members.id;


--
-- Name: max_groups; Type: TABLE; Schema: public; Owner: mdr_user
--

CREATE TABLE public.max_groups (
    id bigint NOT NULL,
    chat_id character varying(64) NOT NULL,
    title character varying(255) NOT NULL,
    active boolean NOT NULL,
    control_message_id character varying(64),
    timezone character varying(64) NOT NULL,
    reminder_hours character varying(32),
    morning_summary_at character varying(16),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.max_groups OWNER TO mdr_user;

--
-- Name: max_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: mdr_user
--

CREATE SEQUENCE public.max_groups_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.max_groups_id_seq OWNER TO mdr_user;

--
-- Name: max_groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mdr_user
--

ALTER SEQUENCE public.max_groups_id_seq OWNED BY public.max_groups.id;


--
-- Name: notification_log; Type: TABLE; Schema: public; Owner: mdr_user
--

CREATE TABLE public.notification_log (
    id bigint NOT NULL,
    notification_key character varying(255) NOT NULL,
    kind character varying(32) NOT NULL,
    group_id bigint,
    report_date date,
    payload_json text,
    status public.notification_status NOT NULL,
    attempts bigint NOT NULL,
    sent_at timestamp with time zone,
    external_message_id character varying(64),
    last_error text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.notification_log OWNER TO mdr_user;

--
-- Name: notification_log_id_seq; Type: SEQUENCE; Schema: public; Owner: mdr_user
--

CREATE SEQUENCE public.notification_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.notification_log_id_seq OWNER TO mdr_user;

--
-- Name: notification_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mdr_user
--

ALTER SEQUENCE public.notification_log_id_seq OWNED BY public.notification_log.id;


--
-- Name: object_stages; Type: TABLE; Schema: public; Owner: mdr_user
--

CREATE TABLE public.object_stages (
    id bigint NOT NULL,
    object_id bigint NOT NULL,
    stage_id bigint NOT NULL,
    active boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.object_stages OWNER TO mdr_user;

--
-- Name: object_stages_id_seq; Type: SEQUENCE; Schema: public; Owner: mdr_user
--

CREATE SEQUENCE public.object_stages_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.object_stages_id_seq OWNER TO mdr_user;

--
-- Name: object_stages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mdr_user
--

ALTER SEQUENCE public.object_stages_id_seq OWNED BY public.object_stages.id;


--
-- Name: objects; Type: TABLE; Schema: public; Owner: mdr_user
--

CREATE TABLE public.objects (
    execution_method public.object_execution_method,
    default_contractor_id bigint,
    id bigint NOT NULL,
    code character varying(64) NOT NULL,
    name character varying(255) NOT NULL,
    search_aliases text,
    active boolean NOT NULL,
    sort_order bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.objects OWNER TO mdr_user;

--
-- Name: objects_id_seq; Type: SEQUENCE; Schema: public; Owner: mdr_user
--

CREATE SEQUENCE public.objects_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.objects_id_seq OWNER TO mdr_user;

--
-- Name: objects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mdr_user
--

ALTER SEQUENCE public.objects_id_seq OWNED BY public.objects.id;


--
-- Name: outbox_events; Type: TABLE; Schema: public; Owner: mdr_user
--

CREATE TABLE public.outbox_events (
    id bigint NOT NULL,
    event_key character varying(255) NOT NULL,
    kind public.outbox_event_kind NOT NULL,
    payload_json text,
    status public.outbox_event_status NOT NULL,
    attempts bigint NOT NULL,
    available_at timestamp with time zone DEFAULT now() NOT NULL,
    last_error text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.outbox_events OWNER TO mdr_user;

--
-- Name: outbox_events_id_seq; Type: SEQUENCE; Schema: public; Owner: mdr_user
--

CREATE SEQUENCE public.outbox_events_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.outbox_events_id_seq OWNER TO mdr_user;

--
-- Name: outbox_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mdr_user
--

ALTER SEQUENCE public.outbox_events_id_seq OWNED BY public.outbox_events.id;


--
-- Name: report_equipment; Type: TABLE; Schema: public; Owner: mdr_user
--

CREATE TABLE public.report_equipment (
    id bigint NOT NULL,
    report_id bigint NOT NULL,
    equipment_type_id bigint NOT NULL,
    equipment_name_snapshot character varying(255) NOT NULL,
    ownership public.equipment_ownership NOT NULL,
    unit_id bigint NOT NULL,
    unit_name_snapshot character varying(64) NOT NULL,
    quantity numeric(14,2) NOT NULL,
    comment text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.report_equipment OWNER TO mdr_user;

--
-- Name: report_equipment_id_seq; Type: SEQUENCE; Schema: public; Owner: mdr_user
--

CREATE SEQUENCE public.report_equipment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.report_equipment_id_seq OWNER TO mdr_user;

--
-- Name: report_equipment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mdr_user
--

ALTER SEQUENCE public.report_equipment_id_seq OWNED BY public.report_equipment.id;


--
-- Name: report_obligations; Type: TABLE; Schema: public; Owner: mdr_user
--

CREATE TABLE public.report_obligations (
    id bigint NOT NULL,
    report_date date NOT NULL,
    assignment_id bigint NOT NULL,
    user_id bigint NOT NULL,
    object_id bigint NOT NULL,
    status public.report_obligation_status NOT NULL,
    due_at timestamp with time zone,
    submitted_at timestamp with time zone,
    report_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.report_obligations OWNER TO mdr_user;

--
-- Name: report_obligations_id_seq; Type: SEQUENCE; Schema: public; Owner: mdr_user
--

CREATE SEQUENCE public.report_obligations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.report_obligations_id_seq OWNER TO mdr_user;

--
-- Name: report_obligations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mdr_user
--

ALTER SEQUENCE public.report_obligations_id_seq OWNED BY public.report_obligations.id;


--
-- Name: report_works; Type: TABLE; Schema: public; Owner: mdr_user
--

CREATE TABLE public.report_works (
    id bigint NOT NULL,
    report_id bigint NOT NULL,
    work_type_id bigint NOT NULL,
    work_name_snapshot character varying(255) NOT NULL,
    work_method_id bigint,
    method_name_snapshot character varying(255),
    unit_id bigint NOT NULL,
    unit_name_snapshot character varying(64) NOT NULL,
    quantity numeric(14,2) NOT NULL,
    comment text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.report_works OWNER TO mdr_user;

--
-- Name: report_works_id_seq; Type: SEQUENCE; Schema: public; Owner: mdr_user
--

CREATE SEQUENCE public.report_works_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.report_works_id_seq OWNER TO mdr_user;

--
-- Name: report_works_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mdr_user
--

ALTER SEQUENCE public.report_works_id_seq OWNED BY public.report_works.id;


--
-- Name: responsible_object_assignments; Type: TABLE; Schema: public; Owner: mdr_user
--

CREATE TABLE public.responsible_object_assignments (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    object_id bigint NOT NULL,
    active_from date NOT NULL,
    active_to date NOT NULL,
    schedule_type public.assignment_schedule_type NOT NULL,
    active boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.responsible_object_assignments OWNER TO mdr_user;

--
-- Name: responsible_object_assignments_id_seq; Type: SEQUENCE; Schema: public; Owner: mdr_user
--

CREATE SEQUENCE public.responsible_object_assignments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.responsible_object_assignments_id_seq OWNER TO mdr_user;

--
-- Name: responsible_object_assignments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mdr_user
--

ALTER SEQUENCE public.responsible_object_assignments_id_seq OWNED BY public.responsible_object_assignments.id;


--
-- Name: stages; Type: TABLE; Schema: public; Owner: mdr_user
--

CREATE TABLE public.stages (
    id bigint NOT NULL,
    code character varying(64) NOT NULL,
    name character varying(255) NOT NULL,
    search_aliases text,
    active boolean NOT NULL,
    sort_order bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.stages OWNER TO mdr_user;

--
-- Name: stages_id_seq; Type: SEQUENCE; Schema: public; Owner: mdr_user
--

CREATE SEQUENCE public.stages_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.stages_id_seq OWNER TO mdr_user;

--
-- Name: stages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mdr_user
--

ALTER SEQUENCE public.stages_id_seq OWNED BY public.stages.id;


--
-- Name: units; Type: TABLE; Schema: public; Owner: mdr_user
--

CREATE TABLE public.units (
    symbol character varying(16) NOT NULL,
    id bigint NOT NULL,
    code character varying(64) NOT NULL,
    name character varying(255) NOT NULL,
    search_aliases text,
    active boolean NOT NULL,
    sort_order bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.units OWNER TO mdr_user;

--
-- Name: units_id_seq; Type: SEQUENCE; Schema: public; Owner: mdr_user
--

CREATE SEQUENCE public.units_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.units_id_seq OWNER TO mdr_user;

--
-- Name: units_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mdr_user
--

ALTER SEQUENCE public.units_id_seq OWNED BY public.units.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: mdr_user
--

CREATE TABLE public.users (
    id bigint NOT NULL,
    max_user_id character varying(64) NOT NULL,
    full_name character varying(255) NOT NULL,
    role public.user_role NOT NULL,
    active boolean NOT NULL,
    private_control_message_id character varying(64),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.users OWNER TO mdr_user;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: mdr_user
--

CREATE SEQUENCE public.users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO mdr_user;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mdr_user
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: work_methods; Type: TABLE; Schema: public; Owner: mdr_user
--

CREATE TABLE public.work_methods (
    id bigint NOT NULL,
    code character varying(64) NOT NULL,
    name character varying(255) NOT NULL,
    search_aliases text,
    active boolean NOT NULL,
    sort_order bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.work_methods OWNER TO mdr_user;

--
-- Name: work_methods_id_seq; Type: SEQUENCE; Schema: public; Owner: mdr_user
--

CREATE SEQUENCE public.work_methods_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.work_methods_id_seq OWNER TO mdr_user;

--
-- Name: work_methods_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mdr_user
--

ALTER SEQUENCE public.work_methods_id_seq OWNED BY public.work_methods.id;


--
-- Name: work_type_methods; Type: TABLE; Schema: public; Owner: mdr_user
--

CREATE TABLE public.work_type_methods (
    id bigint NOT NULL,
    work_type_id bigint NOT NULL,
    work_method_id bigint NOT NULL,
    active boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.work_type_methods OWNER TO mdr_user;

--
-- Name: work_type_methods_id_seq; Type: SEQUENCE; Schema: public; Owner: mdr_user
--

CREATE SEQUENCE public.work_type_methods_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.work_type_methods_id_seq OWNER TO mdr_user;

--
-- Name: work_type_methods_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mdr_user
--

ALTER SEQUENCE public.work_type_methods_id_seq OWNED BY public.work_type_methods.id;


--
-- Name: work_types; Type: TABLE; Schema: public; Owner: mdr_user
--

CREATE TABLE public.work_types (
    default_unit_id bigint,
    id bigint NOT NULL,
    code character varying(64) NOT NULL,
    name character varying(255) NOT NULL,
    search_aliases text,
    active boolean NOT NULL,
    sort_order bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.work_types OWNER TO mdr_user;

--
-- Name: work_types_id_seq; Type: SEQUENCE; Schema: public; Owner: mdr_user
--

CREATE SEQUENCE public.work_types_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.work_types_id_seq OWNER TO mdr_user;

--
-- Name: work_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mdr_user
--

ALTER SEQUENCE public.work_types_id_seq OWNED BY public.work_types.id;


--
-- Name: catalog_imports id; Type: DEFAULT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.catalog_imports ALTER COLUMN id SET DEFAULT nextval('public.catalog_imports_id_seq'::regclass);


--
-- Name: contractors id; Type: DEFAULT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.contractors ALTER COLUMN id SET DEFAULT nextval('public.contractors_id_seq'::regclass);


--
-- Name: daily_reports id; Type: DEFAULT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.daily_reports ALTER COLUMN id SET DEFAULT nextval('public.daily_reports_id_seq'::regclass);


--
-- Name: equipment_types id; Type: DEFAULT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.equipment_types ALTER COLUMN id SET DEFAULT nextval('public.equipment_types_id_seq'::regclass);


--
-- Name: group_members id; Type: DEFAULT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.group_members ALTER COLUMN id SET DEFAULT nextval('public.group_members_id_seq'::regclass);


--
-- Name: max_groups id; Type: DEFAULT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.max_groups ALTER COLUMN id SET DEFAULT nextval('public.max_groups_id_seq'::regclass);


--
-- Name: notification_log id; Type: DEFAULT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.notification_log ALTER COLUMN id SET DEFAULT nextval('public.notification_log_id_seq'::regclass);


--
-- Name: object_stages id; Type: DEFAULT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.object_stages ALTER COLUMN id SET DEFAULT nextval('public.object_stages_id_seq'::regclass);


--
-- Name: objects id; Type: DEFAULT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.objects ALTER COLUMN id SET DEFAULT nextval('public.objects_id_seq'::regclass);


--
-- Name: outbox_events id; Type: DEFAULT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.outbox_events ALTER COLUMN id SET DEFAULT nextval('public.outbox_events_id_seq'::regclass);


--
-- Name: report_equipment id; Type: DEFAULT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.report_equipment ALTER COLUMN id SET DEFAULT nextval('public.report_equipment_id_seq'::regclass);


--
-- Name: report_obligations id; Type: DEFAULT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.report_obligations ALTER COLUMN id SET DEFAULT nextval('public.report_obligations_id_seq'::regclass);


--
-- Name: report_works id; Type: DEFAULT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.report_works ALTER COLUMN id SET DEFAULT nextval('public.report_works_id_seq'::regclass);


--
-- Name: responsible_object_assignments id; Type: DEFAULT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.responsible_object_assignments ALTER COLUMN id SET DEFAULT nextval('public.responsible_object_assignments_id_seq'::regclass);


--
-- Name: stages id; Type: DEFAULT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.stages ALTER COLUMN id SET DEFAULT nextval('public.stages_id_seq'::regclass);


--
-- Name: units id; Type: DEFAULT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.units ALTER COLUMN id SET DEFAULT nextval('public.units_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: work_methods id; Type: DEFAULT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.work_methods ALTER COLUMN id SET DEFAULT nextval('public.work_methods_id_seq'::regclass);


--
-- Name: work_type_methods id; Type: DEFAULT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.work_type_methods ALTER COLUMN id SET DEFAULT nextval('public.work_type_methods_id_seq'::regclass);


--
-- Name: work_types id; Type: DEFAULT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.work_types ALTER COLUMN id SET DEFAULT nextval('public.work_types_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: mdr_user
--

COPY public.alembic_version (version_num) FROM stdin;
b8f81b9a3983
\.


--
-- Data for Name: catalog_imports; Type: TABLE DATA; Schema: public; Owner: mdr_user
--

COPY public.catalog_imports (id, filename, status, summary_json, errors_json, created_by, created_at, applied_at) FROM stdin;
\.


--
-- Data for Name: contractors; Type: TABLE DATA; Schema: public; Owner: mdr_user
--

COPY public.contractors (id, code, name, search_aliases, active, sort_order, created_at, updated_at) FROM stdin;
1	own	Собственные силы	\N	t	\N	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
2	spetstroy	ООО СпецСтрой	\N	t	\N	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
\.


--
-- Data for Name: daily_reports; Type: TABLE DATA; Schema: public; Owner: mdr_user
--

COPY public.daily_reports (id, report_date, responsible_user_id, object_id, stage_id, contractor_id, comment, staff_itr, staff_internal, staff_external, soil_export_m3, status, idempotency_key, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: equipment_types; Type: TABLE DATA; Schema: public; Owner: mdr_user
--

COPY public.equipment_types (default_unit_id, id, code, name, search_aliases, active, sort_order, created_at, updated_at) FROM stdin;
5	1	exc-200	Экскаватор 200	\N	t	\N	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
5	2	dump-20	Самосвал 20т	\N	t	\N	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
5	3	bulldozer	Бульдозер	\N	t	\N	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
\.


--
-- Data for Name: group_members; Type: TABLE DATA; Schema: public; Owner: mdr_user
--

COPY public.group_members (id, group_id, user_id, active, created_at, updated_at) FROM stdin;
1	1	2	t	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
2	1	3	t	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
3	1	4	t	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
\.


--
-- Data for Name: max_groups; Type: TABLE DATA; Schema: public; Owner: mdr_user
--

COPY public.max_groups (id, chat_id, title, active, control_message_id, timezone, reminder_hours, morning_summary_at, created_at, updated_at) FROM stdin;
1	max-group-1	Строительный участок №1	t	\N	Europe/Moscow	20:00,20:30	08:00	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
\.


--
-- Data for Name: notification_log; Type: TABLE DATA; Schema: public; Owner: mdr_user
--

COPY public.notification_log (id, notification_key, kind, group_id, report_date, payload_json, status, attempts, sent_at, external_message_id, last_error, created_at, updated_at) FROM stdin;
1	morning_summary:1:2026-07-13	morning_summary	1	2026-07-13	\N	failed	0	\N	\N	[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)	2026-07-14 09:49:33.880444+00	2026-07-14 09:49:33.880444+00
\.


--
-- Data for Name: object_stages; Type: TABLE DATA; Schema: public; Owner: mdr_user
--

COPY public.object_stages (id, object_id, stage_id, active, created_at, updated_at) FROM stdin;
1	1	1	t	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
2	1	2	t	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
3	2	2	t	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
4	2	3	t	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
\.


--
-- Data for Name: objects; Type: TABLE DATA; Schema: public; Owner: mdr_user
--

COPY public.objects (execution_method, default_contractor_id, id, code, name, search_aliases, active, sort_order, created_at, updated_at) FROM stdin;
own	1	1	obj-1	ЖК Северный объект 1	\N	t	\N	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
contractor	2	2	obj-2	ЖК Северный объект 2	\N	t	\N	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
\.


--
-- Data for Name: outbox_events; Type: TABLE DATA; Schema: public; Owner: mdr_user
--

COPY public.outbox_events (id, event_key, kind, payload_json, status, attempts, available_at, last_error, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: report_equipment; Type: TABLE DATA; Schema: public; Owner: mdr_user
--

COPY public.report_equipment (id, report_id, equipment_type_id, equipment_name_snapshot, ownership, unit_id, unit_name_snapshot, quantity, comment, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: report_obligations; Type: TABLE DATA; Schema: public; Owner: mdr_user
--

COPY public.report_obligations (id, report_date, assignment_id, user_id, object_id, status, due_at, submitted_at, report_id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: report_works; Type: TABLE DATA; Schema: public; Owner: mdr_user
--

COPY public.report_works (id, report_id, work_type_id, work_name_snapshot, work_method_id, method_name_snapshot, unit_id, unit_name_snapshot, quantity, comment, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: responsible_object_assignments; Type: TABLE DATA; Schema: public; Owner: mdr_user
--

COPY public.responsible_object_assignments (id, user_id, object_id, active_from, active_to, schedule_type, active, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: stages; Type: TABLE DATA; Schema: public; Owner: mdr_user
--

COPY public.stages (id, code, name, search_aliases, active, sort_order, created_at, updated_at) FROM stdin;
1	prep	Подготовительные работы	\N	t	\N	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
2	zero	Нулевой цикл	\N	t	\N	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
3	frame	Каркас	\N	t	\N	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
4	facade	Фасад	\N	t	\N	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
\.


--
-- Data for Name: units; Type: TABLE DATA; Schema: public; Owner: mdr_user
--

COPY public.units (symbol, id, code, name, search_aliases, active, sort_order, created_at, updated_at) FROM stdin;
м³	1	m3	кубометр	\N	t	\N	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
м²	2	m2	квадратный метр	\N	t	\N	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
т	3	ton	тонна	\N	t	\N	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
шт	4	pcs	штука	\N	t	\N	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
ч/м	5	hm	час-машина	\N	t	\N	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
км	6	km	километр	\N	t	\N	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: mdr_user
--

COPY public.users (id, max_user_id, full_name, role, active, private_control_message_id, created_at, updated_at) FROM stdin;
1	dev-user	Dev User	responsible	t	\N	2026-07-14 09:23:34.286398+00	2026-07-14 09:23:34.286398+00
2	max-manager-1	Петров М.И.	manager	t	\N	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
3	max-resp-1	Иванов А.В.	responsible	t	\N	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
4	max-resp-2	Сидоров К.П.	responsible	t	\N	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
\.


--
-- Data for Name: work_methods; Type: TABLE DATA; Schema: public; Owner: mdr_user
--

COPY public.work_methods (id, code, name, search_aliases, active, sort_order, created_at, updated_at) FROM stdin;
1	manual	Вручную	\N	t	\N	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
2	machine	Механизированно	\N	t	\N	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
\.


--
-- Data for Name: work_type_methods; Type: TABLE DATA; Schema: public; Owner: mdr_user
--

COPY public.work_type_methods (id, work_type_id, work_method_id, active, created_at, updated_at) FROM stdin;
1	1	1	t	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
2	1	2	t	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
3	2	2	t	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
4	3	1	t	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
\.


--
-- Data for Name: work_types; Type: TABLE DATA; Schema: public; Owner: mdr_user
--

COPY public.work_types (default_unit_id, id, code, name, search_aliases, active, sort_order, created_at, updated_at) FROM stdin;
1	1	dig	Земляные работы	\N	t	\N	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
1	2	concrete	Бетонные работы	\N	t	\N	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
2	3	formwork	Опалубка	\N	t	\N	2026-07-14 09:47:43.666868+00	2026-07-14 09:47:43.666868+00
\.


--
-- Name: catalog_imports_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mdr_user
--

SELECT pg_catalog.setval('public.catalog_imports_id_seq', 1, false);


--
-- Name: contractors_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mdr_user
--

SELECT pg_catalog.setval('public.contractors_id_seq', 2, true);


--
-- Name: daily_reports_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mdr_user
--

SELECT pg_catalog.setval('public.daily_reports_id_seq', 1, false);


--
-- Name: equipment_types_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mdr_user
--

SELECT pg_catalog.setval('public.equipment_types_id_seq', 3, true);


--
-- Name: group_members_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mdr_user
--

SELECT pg_catalog.setval('public.group_members_id_seq', 3, true);


--
-- Name: max_groups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mdr_user
--

SELECT pg_catalog.setval('public.max_groups_id_seq', 1, true);


--
-- Name: notification_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mdr_user
--

SELECT pg_catalog.setval('public.notification_log_id_seq', 1, true);


--
-- Name: object_stages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mdr_user
--

SELECT pg_catalog.setval('public.object_stages_id_seq', 4, true);


--
-- Name: objects_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mdr_user
--

SELECT pg_catalog.setval('public.objects_id_seq', 2, true);


--
-- Name: outbox_events_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mdr_user
--

SELECT pg_catalog.setval('public.outbox_events_id_seq', 1, false);


--
-- Name: report_equipment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mdr_user
--

SELECT pg_catalog.setval('public.report_equipment_id_seq', 1, false);


--
-- Name: report_obligations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mdr_user
--

SELECT pg_catalog.setval('public.report_obligations_id_seq', 1, false);


--
-- Name: report_works_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mdr_user
--

SELECT pg_catalog.setval('public.report_works_id_seq', 1, false);


--
-- Name: responsible_object_assignments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mdr_user
--

SELECT pg_catalog.setval('public.responsible_object_assignments_id_seq', 1, false);


--
-- Name: stages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mdr_user
--

SELECT pg_catalog.setval('public.stages_id_seq', 4, true);


--
-- Name: units_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mdr_user
--

SELECT pg_catalog.setval('public.units_id_seq', 6, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mdr_user
--

SELECT pg_catalog.setval('public.users_id_seq', 4, true);


--
-- Name: work_methods_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mdr_user
--

SELECT pg_catalog.setval('public.work_methods_id_seq', 2, true);


--
-- Name: work_type_methods_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mdr_user
--

SELECT pg_catalog.setval('public.work_type_methods_id_seq', 4, true);


--
-- Name: work_types_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mdr_user
--

SELECT pg_catalog.setval('public.work_types_id_seq', 3, true);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: catalog_imports catalog_imports_pkey; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.catalog_imports
    ADD CONSTRAINT catalog_imports_pkey PRIMARY KEY (id);


--
-- Name: contractors contractors_code_key; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.contractors
    ADD CONSTRAINT contractors_code_key UNIQUE (code);


--
-- Name: contractors contractors_pkey; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.contractors
    ADD CONSTRAINT contractors_pkey PRIMARY KEY (id);


--
-- Name: daily_reports daily_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.daily_reports
    ADD CONSTRAINT daily_reports_pkey PRIMARY KEY (id);


--
-- Name: equipment_types equipment_types_code_key; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.equipment_types
    ADD CONSTRAINT equipment_types_code_key UNIQUE (code);


--
-- Name: equipment_types equipment_types_pkey; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.equipment_types
    ADD CONSTRAINT equipment_types_pkey PRIMARY KEY (id);


--
-- Name: group_members group_members_pkey; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_pkey PRIMARY KEY (id);


--
-- Name: max_groups max_groups_chat_id_key; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.max_groups
    ADD CONSTRAINT max_groups_chat_id_key UNIQUE (chat_id);


--
-- Name: max_groups max_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.max_groups
    ADD CONSTRAINT max_groups_pkey PRIMARY KEY (id);


--
-- Name: notification_log notification_log_pkey; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.notification_log
    ADD CONSTRAINT notification_log_pkey PRIMARY KEY (id);


--
-- Name: object_stages object_stages_pkey; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.object_stages
    ADD CONSTRAINT object_stages_pkey PRIMARY KEY (id);


--
-- Name: objects objects_code_key; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.objects
    ADD CONSTRAINT objects_code_key UNIQUE (code);


--
-- Name: objects objects_pkey; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.objects
    ADD CONSTRAINT objects_pkey PRIMARY KEY (id);


--
-- Name: outbox_events outbox_events_pkey; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.outbox_events
    ADD CONSTRAINT outbox_events_pkey PRIMARY KEY (id);


--
-- Name: report_equipment report_equipment_pkey; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.report_equipment
    ADD CONSTRAINT report_equipment_pkey PRIMARY KEY (id);


--
-- Name: report_obligations report_obligations_pkey; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.report_obligations
    ADD CONSTRAINT report_obligations_pkey PRIMARY KEY (id);


--
-- Name: report_works report_works_pkey; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.report_works
    ADD CONSTRAINT report_works_pkey PRIMARY KEY (id);


--
-- Name: responsible_object_assignments responsible_object_assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.responsible_object_assignments
    ADD CONSTRAINT responsible_object_assignments_pkey PRIMARY KEY (id);


--
-- Name: stages stages_code_key; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.stages
    ADD CONSTRAINT stages_code_key UNIQUE (code);


--
-- Name: stages stages_pkey; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.stages
    ADD CONSTRAINT stages_pkey PRIMARY KEY (id);


--
-- Name: units units_code_key; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.units
    ADD CONSTRAINT units_code_key UNIQUE (code);


--
-- Name: units units_pkey; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.units
    ADD CONSTRAINT units_pkey PRIMARY KEY (id);


--
-- Name: daily_reports uq_daily_report_idempotency_key; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.daily_reports
    ADD CONSTRAINT uq_daily_report_idempotency_key UNIQUE (idempotency_key);


--
-- Name: group_members uq_group_member; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT uq_group_member UNIQUE (group_id, user_id);


--
-- Name: notification_log uq_notification_key; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.notification_log
    ADD CONSTRAINT uq_notification_key UNIQUE (notification_key);


--
-- Name: object_stages uq_object_stage; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.object_stages
    ADD CONSTRAINT uq_object_stage UNIQUE (object_id, stage_id);


--
-- Name: report_obligations uq_obligation_date_assignment; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.report_obligations
    ADD CONSTRAINT uq_obligation_date_assignment UNIQUE (report_date, assignment_id);


--
-- Name: outbox_events uq_outbox_event_key; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.outbox_events
    ADD CONSTRAINT uq_outbox_event_key UNIQUE (event_key);


--
-- Name: responsible_object_assignments uq_responsible_assignment; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.responsible_object_assignments
    ADD CONSTRAINT uq_responsible_assignment UNIQUE (user_id, object_id);


--
-- Name: work_type_methods uq_work_type_method; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.work_type_methods
    ADD CONSTRAINT uq_work_type_method UNIQUE (work_type_id, work_method_id);


--
-- Name: users users_max_user_id_key; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_max_user_id_key UNIQUE (max_user_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: work_methods work_methods_code_key; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.work_methods
    ADD CONSTRAINT work_methods_code_key UNIQUE (code);


--
-- Name: work_methods work_methods_pkey; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.work_methods
    ADD CONSTRAINT work_methods_pkey PRIMARY KEY (id);


--
-- Name: work_type_methods work_type_methods_pkey; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.work_type_methods
    ADD CONSTRAINT work_type_methods_pkey PRIMARY KEY (id);


--
-- Name: work_types work_types_code_key; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.work_types
    ADD CONSTRAINT work_types_code_key UNIQUE (code);


--
-- Name: work_types work_types_pkey; Type: CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.work_types
    ADD CONSTRAINT work_types_pkey PRIMARY KEY (id);


--
-- Name: daily_reports daily_reports_contractor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.daily_reports
    ADD CONSTRAINT daily_reports_contractor_id_fkey FOREIGN KEY (contractor_id) REFERENCES public.contractors(id);


--
-- Name: daily_reports daily_reports_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.daily_reports
    ADD CONSTRAINT daily_reports_object_id_fkey FOREIGN KEY (object_id) REFERENCES public.objects(id);


--
-- Name: daily_reports daily_reports_responsible_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.daily_reports
    ADD CONSTRAINT daily_reports_responsible_user_id_fkey FOREIGN KEY (responsible_user_id) REFERENCES public.users(id);


--
-- Name: daily_reports daily_reports_stage_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.daily_reports
    ADD CONSTRAINT daily_reports_stage_id_fkey FOREIGN KEY (stage_id) REFERENCES public.stages(id);


--
-- Name: equipment_types equipment_types_default_unit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.equipment_types
    ADD CONSTRAINT equipment_types_default_unit_id_fkey FOREIGN KEY (default_unit_id) REFERENCES public.units(id);


--
-- Name: group_members group_members_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.max_groups(id);


--
-- Name: group_members group_members_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: notification_log notification_log_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.notification_log
    ADD CONSTRAINT notification_log_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.max_groups(id);


--
-- Name: object_stages object_stages_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.object_stages
    ADD CONSTRAINT object_stages_object_id_fkey FOREIGN KEY (object_id) REFERENCES public.objects(id);


--
-- Name: object_stages object_stages_stage_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.object_stages
    ADD CONSTRAINT object_stages_stage_id_fkey FOREIGN KEY (stage_id) REFERENCES public.stages(id);


--
-- Name: objects objects_default_contractor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.objects
    ADD CONSTRAINT objects_default_contractor_id_fkey FOREIGN KEY (default_contractor_id) REFERENCES public.contractors(id);


--
-- Name: report_equipment report_equipment_equipment_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.report_equipment
    ADD CONSTRAINT report_equipment_equipment_type_id_fkey FOREIGN KEY (equipment_type_id) REFERENCES public.equipment_types(id);


--
-- Name: report_equipment report_equipment_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.report_equipment
    ADD CONSTRAINT report_equipment_report_id_fkey FOREIGN KEY (report_id) REFERENCES public.daily_reports(id);


--
-- Name: report_equipment report_equipment_unit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.report_equipment
    ADD CONSTRAINT report_equipment_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES public.units(id);


--
-- Name: report_obligations report_obligations_assignment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.report_obligations
    ADD CONSTRAINT report_obligations_assignment_id_fkey FOREIGN KEY (assignment_id) REFERENCES public.responsible_object_assignments(id);


--
-- Name: report_obligations report_obligations_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.report_obligations
    ADD CONSTRAINT report_obligations_object_id_fkey FOREIGN KEY (object_id) REFERENCES public.objects(id);


--
-- Name: report_obligations report_obligations_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.report_obligations
    ADD CONSTRAINT report_obligations_report_id_fkey FOREIGN KEY (report_id) REFERENCES public.daily_reports(id);


--
-- Name: report_obligations report_obligations_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.report_obligations
    ADD CONSTRAINT report_obligations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: report_works report_works_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.report_works
    ADD CONSTRAINT report_works_report_id_fkey FOREIGN KEY (report_id) REFERENCES public.daily_reports(id);


--
-- Name: report_works report_works_unit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.report_works
    ADD CONSTRAINT report_works_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES public.units(id);


--
-- Name: report_works report_works_work_method_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.report_works
    ADD CONSTRAINT report_works_work_method_id_fkey FOREIGN KEY (work_method_id) REFERENCES public.work_methods(id);


--
-- Name: report_works report_works_work_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.report_works
    ADD CONSTRAINT report_works_work_type_id_fkey FOREIGN KEY (work_type_id) REFERENCES public.work_types(id);


--
-- Name: responsible_object_assignments responsible_object_assignments_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.responsible_object_assignments
    ADD CONSTRAINT responsible_object_assignments_object_id_fkey FOREIGN KEY (object_id) REFERENCES public.objects(id);


--
-- Name: responsible_object_assignments responsible_object_assignments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.responsible_object_assignments
    ADD CONSTRAINT responsible_object_assignments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: work_type_methods work_type_methods_work_method_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.work_type_methods
    ADD CONSTRAINT work_type_methods_work_method_id_fkey FOREIGN KEY (work_method_id) REFERENCES public.work_methods(id);


--
-- Name: work_type_methods work_type_methods_work_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.work_type_methods
    ADD CONSTRAINT work_type_methods_work_type_id_fkey FOREIGN KEY (work_type_id) REFERENCES public.work_types(id);


--
-- Name: work_types work_types_default_unit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mdr_user
--

ALTER TABLE ONLY public.work_types
    ADD CONSTRAINT work_types_default_unit_id_fkey FOREIGN KEY (default_unit_id) REFERENCES public.units(id);


--
-- PostgreSQL database dump complete
--

\unrestrict 2qTZ5vb9fHGLog1fKbxhThdcfwi4fntrHo0lbqIHQfXtbsvCLUzBhY8dqpwV8cE

