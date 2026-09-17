create table if not exists properties (
  property_id text primary key,
  source text not null,
  source_url text,
  source_type text,
  category text not null,
  sub_category text,
  title text,
  property_name text,
  latitude double precision not null,
  longitude double precision not null,
  address text,
  district text,
  city text,
  price double precision,
  price_min double precision,
  price_max double precision,
  price_unit text,
  area_land_m2 double precision,
  area_building_m2 double precision,
  price_per_m2 double precision,
  listing_type text,
  sale_or_rent text not null,
  bedroom integer,
  bathroom integer,
  floor integer,
  property_status text,
  date_listed text,
  date_updated text,
  data_timestamp text,
  confidence_score text,
  geometry_source text,
  corridor_id text,
  corridor_type text,
  distance_to_corridor double precision,
  distance_to_station double precision,
  nearest_station text,
  existing_corridor_id text,
  existing_distance_m double precision,
  masterplan_corridor_id text,
  masterplan_distance_m double precision,
  cascade_corridor_id text,
  cascade_distance_m double precision,
  local_price_index double precision,
  price_class text,
  price_label text,
  outlier_flag integer not null default 0,
  cell_id text
);
create index if not exists properties_bbox_idx on properties (longitude, latitude);
create index if not exists properties_cat_idx on properties (category);
create index if not exists properties_class_idx on properties (price_class);
create index if not exists properties_sale_idx on properties (sale_or_rent);
create index if not exists properties_corr_idx on properties (corridor_type, corridor_id);

create table if not exists property_cache (
  cache_key text primary key,
  payload text not null,
  updated_at timestamptz not null default now()
);
