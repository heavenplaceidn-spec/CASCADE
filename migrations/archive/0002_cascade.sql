create table if not exists cascade_sources (
  dataset text primary key,
  source text not null,
  source_type text not null,
  geometry_type text,
  crs text not null default 'EPSG:4326',
  feature_count integer not null default 0,
  notes text
);
