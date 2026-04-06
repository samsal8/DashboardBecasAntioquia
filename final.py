import pandas as pd
import streamlit as st
import plotly.express as px


# Compatibilidad con varias versiones de Streamlit
try:
   cache_decorator = st.cache_data
except AttributeError:
   cache_decorator = st.cache


@cache_decorator
def load_data(path='datos.csv'):
   df = pd.read_csv(path, low_memory=False)


   # Normalizaciones básicas
   for col in ['GRADUADO', 'VICTIMA DEL CONFLICTO ARMADO']:
       if col in df.columns:
           df[col] = (df[col]
                      .astype(str)
                      .str.strip()
                      .str.upper()
                      .replace({'SI': 1, 'NO': 0}))
           df[col] = pd.to_numeric(df[col], errors='coerce')


   if 'ESTRATO' in df.columns:
       df['ESTRATO'] = (df['ESTRATO'].astype(str)
                        .str.replace('ESTRATO', '', regex=False)
                        .str.strip())
       df['ESTRATO'] = pd.to_numeric(df['ESTRATO'], errors='coerce')


   if 'FECHA DE NACIMIENTO' in df.columns:
       df['FECHA DE NACIMIENTO'] = pd.to_datetime(df['FECHA DE NACIMIENTO'], errors='coerce')
       age_years = (pd.Timestamp('today') - df['FECHA DE NACIMIENTO']).dt.days / 365.25
       df['EDAD_ACTUAL'] = pd.to_numeric(age_years, errors='coerce')


   if 'CONVOCATORIA' in df.columns:
       # Eliminar caracteres no numéricos y convertir a número. Los valores inválidos se vuelven NaN.
       df['CONVOCATORIA'] = df['CONVOCATORIA'].astype(str).str.replace('[^0-9]', '', regex=True)
       df['CONVOCATORIA'] = pd.to_numeric(df['CONVOCATORIA'], errors='coerce')


   return df




def main():
   st.set_page_config(page_title='Dashboard Subsidios Educación Antioquia', layout='wide')
   st.title('📊 Dashboard de programas de acceso a educación - Antioquia')
   st.write('Dataset: beneficiarios de subsidios, becas y créditos condonables (Antioquia).')


   try:
       df = load_data('datos.csv')
   except FileNotFoundError:
       st.error('No se encontró el archivo datos.csv. Asegúrate de tenerlo en el mismo directorio que app.py.')
       return
   except Exception as e:
       st.error(f'Error al cargar datos: {e}')
       return


   if df.empty:
       st.warning('El DataFrame cargado está vacío. Verifica el archivo de datos.')
       return


   st.sidebar.header('Filtros')


   # Filtros disponibles en sidebar
   dept_res = 'DEPARTAMENTO DE RESIDENCIA'
   grado = 'GRADUADO'
   muni_res = 'MUNICIPIO DE RESIDENCIA'
   conv = 'CONVOCATORIA'


   if dept_res in df.columns:
       departamentos = sorted(df[dept_res].dropna().unique().astype(str))
       selected_departamentos = st.sidebar.multiselect('Departamento de residencia', departamentos, default=None)
       if selected_departamentos:
           df = df[df[dept_res].astype(str).isin(selected_departamentos)]


   if muni_res in df.columns:
       municipios = sorted(df[muni_res].dropna().unique().astype(str))
       selected_municipios = st.sidebar.multiselect('Municipio de residencia', municipios, default=None)
       if selected_municipios:
           df = df[df[muni_res].astype(str).isin(selected_municipios)]


   if conv in df.columns:
       convocatorias = df[conv].dropna().unique()
       safe_conv = []
       for x in convocatorias:
           try:
               # Puede venir como float, texto, etc.
               safe_conv.append(int(float(x)))
           except Exception:
               continue
       safe_conv = sorted(set(safe_conv))


       if safe_conv:
           selected_conv = st.sidebar.multiselect('Convocatoria (año/corte)', safe_conv, default=None)
           if selected_conv:
               df = df[df[conv].astype(float).isin([float(v) for v in selected_conv])]


   if grado in df.columns:
       estado_grado = st.sidebar.radio('Graduado?', options=['Todos', 'Sí', 'No'])
       if estado_grado == 'Sí':
           df = df[df[grado] == 1]
       elif estado_grado == 'No':
           df = df[df[grado] == 0]


   if 'VICTIMA DEL CONFLICTO ARMADO' in df.columns:
       victimas = st.sidebar.selectbox('Victima conflicto armado', options=['Todos', 'Sí', 'No'])
       if victimas == 'Sí':
           df = df[df['VICTIMA DEL CONFLICTO ARMADO'] == 1]
       elif victimas == 'No':
           df = df[df['VICTIMA DEL CONFLICTO ARMADO'] == 0]


   # KPI
   total = len(df)
   total_graduados = int(df[grado].sum()) if grado in df.columns and pd.api.types.is_numeric_dtype(df[grado]) else 0
   pct_graduados = total_graduados / total * 100 if total > 0 else 0


   col1, col2, col3, col4 = st.columns(4)
   col1.metric('Total beneficiarios', total)
   col2.metric('Total graduados', total_graduados)
   col3.metric('Graduación (%)', f'{pct_graduados:.2f}%')
   if 'EDAD_ACTUAL' in df.columns:
       col4.metric('Edad promedio', f'{df["EDAD_ACTUAL"].mean():.1f}')


   st.markdown('---')


   st.subheader('Top 5 municipios por número de graduados (residencia)')
   if 'MUNICIPIO DE NACIMIENTO' in df.columns and grado in df.columns:
       graduates_by_municipio = (df.groupby('MUNICIPIO DE RESIDENCIA')[grado]
                                  .sum()
                                  .sort_values(ascending=False)
                                  .reset_index())
       top_5_mun = graduates_by_municipio.head(5)
       fig_top5 = px.bar(top_5_mun, x='MUNICIPIO DE RESIDENCIA', y=grado,
                         title='Top 5 Municipios de Residencia por Número de Graduados',
                         labels={grado: 'Número de Graduados'},
                         color='MUNICIPIO DE RESIDENCIA')
       st.plotly_chart(fig_top5, use_container_width=True)


   st.subheader('Top 5 municipios por participación vs tasa de graduación')
   if 'MUNICIPIO DE RESIDENCIA' in df.columns and grado in df.columns:
       total_participantes_by_municipio = (df.groupby('MUNICIPIO DE RESIDENCIA').size()
                                          .reset_index(name='TOTAL_PARTICIPANTES'))
       top5_part = total_participantes_by_municipio.sort_values('TOTAL_PARTICIPANTES', ascending=False).head(5)
       df_top5_part = df[df['MUNICIPIO DE RESIDENCIA'].isin(top5_part['MUNICIPIO DE RESIDENCIA'])]


       plot_data_comparison = (df_top5_part.groupby('MUNICIPIO DE RESIDENCIA').agg(
           GRADUADOS=(grado, 'sum'),
           TOTAL_PARTICIPANTES=('MUNICIPIO DE RESIDENCIA', 'size'))
           .reset_index())
       plot_data_comparison['PORCENTAJE_GRADUADOS'] = plot_data_comparison['GRADUADOS'] / plot_data_comparison['TOTAL_PARTICIPANTES'] * 100


       fig3 = px.bar(plot_data_comparison, x='MUNICIPIO DE RESIDENCIA', y='PORCENTAJE_GRADUADOS',
                     title='Porcentaje de Graduados por Municipio (Top 5 en Participación)',
                     labels={'PORCENTAJE_GRADUADOS': 'Porcentaje de Graduados'},
                     color='MUNICIPIO DE RESIDENCIA')
       st.plotly_chart(fig3, use_container_width=True)


   st.subheader('Mapa geográfico (Antioquia) de beneficiarios por municipio')
   if 'MUNICIPIO DE RESIDENCIA' in df.columns:
       import unicodedata


       def normalize_name(name):
           if not isinstance(name, str):
               return ''
           name = name.strip().upper()
           name = ''.join(c for c in unicodedata.normalize('NFKD', name) if not unicodedata.combining(c))
           return name


       df_geo = df.groupby('MUNICIPIO DE RESIDENCIA').size().reset_index(name='BENEFICIARIOS')
       df_geo['MUNICIPIO_DE_RESIDENCIA'] = df_geo['MUNICIPIO DE RESIDENCIA'].apply(normalize_name)


       geojson_path = 'municipios_antioquia.geojson'
       geojson_data = None


       try:
           import os, json, requests


           if not os.path.exists(geojson_path):
               st.info(f"GeoJSON '{geojson_path}' no encontrado. Intentando descargar automáticamente...")
               url_candidates = [
                   'https://drive.google.com/uc?id=1Y0EHHnvH6ny3w5-57QrpCHd62ZJ0lxD4'
               ]
               for url in url_candidates:
                   try:
                       r = requests.get(url, timeout=20)
                       if r.status_code == 200 and r.text.strip():
                           with open(geojson_path, 'w', encoding='utf-8') as f_out:
                               f_out.write(r.text)
                           st.success(f"Descargado GeoJSON desde {url}")
                           break
                   except Exception as ex:
                       st.warning(f"No se pudo descargar el GeoJSON desde {url}. Error: {ex}")
                       continue


           with open(geojson_path, 'r', encoding='utf-8') as f_geo:
               geojson_data = json.load(f_geo)


           if not geojson_data or 'features' not in geojson_data:
               raise ValueError('GeoJSON invalido o sin features')


           for feature in geojson_data.get('features', []):
               props = feature.get('properties', {})
               nombre = str(
                   props.get('NOMBRE_MPI', '') or
                   props.get('NOMBRE_CAB', '') or
                   props.get('NOMBRE_MUN', '') or
                   props.get('NOMBRE', '') or
                   props.get('municipio', '')
               ).upper().strip()
               feature['properties']['MUNICIPIO_DE_RESIDENCIA'] = nombre


           df_geo_agg = df_geo.groupby('MUNICIPIO_DE_RESIDENCIA', as_index=False).agg({'BENEFICIARIOS': 'sum'})


           # Emparejar con geojson mediante correspondencia difusa para evitar perdidas parciales
           import difflib


           available_map = {f['properties']['MUNICIPIO_DE_RESIDENCIA'] for f in geojson_data.get('features', []) if 'properties' in f}
           df_geo_agg['MUNICIPIO_MAP'] = df_geo_agg['MUNICIPIO_DE_RESIDENCIA']


           unmatched = []
           for mun in df_geo_agg['MUNICIPIO_DE_RESIDENCIA']:
               if mun not in available_map:
                   closest = difflib.get_close_matches(mun, sorted(available_map), n=1, cutoff=0.72)
                   if closest:
                       df_geo_agg.loc[df_geo_agg['MUNICIPIO_DE_RESIDENCIA'] == mun, 'MUNICIPIO_MAP'] = closest[0]
                   else:
                       unmatched.append(mun)


           matched = df_geo_agg[df_geo_agg['MUNICIPIO_MAP'].isin(available_map)]
           st.write(f"Municipios con datos en dataframe: {len(df_geo_agg)}, municipios georreferenciados: {len(matched)}")
           if unmatched:
               st.warning(f"No resueltos en GeoJSON ({len(unmatched)}): {', '.join(unmatched[:20])}{'...' if len(unmatched)>20 else ''}")


           # Crear DataFrame con todos los municipios del GeoJSON para pintar con 0 si no tiene dato
           all_municipios = pd.DataFrame({'MUNICIPIO_MAP': sorted(available_map)})
           all_municipios = all_municipios.merge(matched[['MUNICIPIO_MAP', 'BENEFICIARIOS']], on='MUNICIPIO_MAP', how='left')
           all_municipios['BENEFICIARIOS'] = all_municipios['BENEFICIARIOS'].fillna(0)


           fig_map = px.choropleth_mapbox(
               all_municipios,
               geojson=geojson_data,
               locations='MUNICIPIO_MAP',
               featureidkey='properties.MUNICIPIO_DE_RESIDENCIA',
               color='BENEFICIARIOS',
               color_continuous_scale='Viridis',
               mapbox_style='carto-positron',
               zoom=7,
               center={'lat': 6.2200, 'lon': -75.5900},
               opacity=0.6,
               labels={'BENEFICIARIOS': 'N° Beneficiarios'},
               title='Mapa de Antioquia: beneficiarios por municipio de residencia'
           )


           fig_map.update_layout(margin={'r':0,'t':40,'l':0,'b':0})
           st.plotly_chart(fig_map, use_container_width=True)


       except Exception as e:
           st.warning('No se pudo generar el mapa de Antioquia. Comprueba que existe o se descargó correctamente el geojson y que la librería requests está instalada. Detalle: ' + str(e))

#AQUI

   st.subheader('Graduados vs víctimas del conflicto armando')
   if grado in df.columns and 'VICTIMA DEL CONFLICTO ARMADO' in df.columns:
       total_graduados = int(df[grado].sum())
       graduados_victimas = int(df[(df[grado] == 1) & (df['VICTIMA DEL CONFLICTO ARMADO'] == 1)][grado].sum())
       df_vic = pd.DataFrame({'Categoría': ['Total Graduados', 'Graduados Víctimas del Conflicto'],
                              'Cantidad': [total_graduados, graduados_victimas]})
       fig4 = px.bar(df_vic, x='Categoría', y='Cantidad', title='Graduados vs Graduados Víctimas del Conflicto',
                     text='Cantidad', color='Categoría')
       fig4.update_traces(textposition='outside')
       st.plotly_chart(fig4, use_container_width=True)


   st.subheader('Estrato vs proporción de graduados')
   if 'ESTRATO' in df.columns and grado in df.columns:
       estrato_stats = (df.groupby('ESTRATO')[grado]
                        .agg(['count', 'sum'])
                        .rename(columns={'count': 'Total', 'sum': 'Graduados'}))
       estrato_stats['TasaGraduacion'] = estrato_stats['Graduados'] / estrato_stats['Total'] * 100
       fig3 = px.bar(estrato_stats.reset_index(), x='ESTRATO', y='TasaGraduacion', title='Tasa de graduación por estrato', labels={'TasaGraduacion': 'Graduación (%)'}, color='ESTRATO')
       st.plotly_chart(fig3, use_container_width=True)


   st.subheader('Fuente de datos y vista de registros')
   st.write('Se muestran los primeros 100 registros filtrados.')
   st.dataframe(df.head(100), use_container_width=True)


   st.caption('Nota: se recomienda usar datos limpios en el CSV local `datos.csv` con las columnas esperadas.')




if __name__ == '__main__':
   main()
