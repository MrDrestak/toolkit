import streamlit as st
import zipfile
import csv
import os
import io
from datetime import datetime
import shutil

st.set_page_config(page_title="Procesador de Posiciones", layout="centered")

# Crédito en la parte superior con botón (i)
col1, col2 = st.columns([0.95, 0.05])
with col1:
    st.title("🗂️ Procesador de CSV - Posiciones")
#with col2:
#    if st.button("ℹ️", key="info_btn", help="Información del creador"):
#        st.session_state.show_info = True

# Mostrar recuadro de información si se presionó el botón
#if st.session_state.get("show_info", False):
#    st.info("**Elaborado por:** Walter Pacora Rodriguez (108763)")
#    if st.button("Cerrar", key="close_info"):
#        st.session_state.show_info = False

#st.markdown("---")
#st.markdown("*Elaborado por Walter Pacora Rodriguez (108763)*")
#st.markdown("---")

# Inicializa estado
if "procesado" not in st.session_state:
    st.session_state.procesado = False
    st.session_state.pais = None
    st.session_state.estado = None

# Paso 1: Seleccionar País
st.subheader("Paso 1: Selecciona el País")
col1, col2 = st.columns(2)

with col1:
    if st.button("🇵🇪 PERÚ", key="peru", use_container_width=True, help="Mantener 2301, 2101"):
        st.session_state.pais = "Peru"

with col2:
    if st.button("🇨🇱 CHILE", key="chile", use_container_width=True, help="Excluir 2301, 2101"):
        st.session_state.pais = "Chile"

if st.session_state.pais:
    st.success(f"✓ País seleccionado: {st.session_state.pais}")
    
    # Paso 2: Seleccionar Filtro de Estado
    st.subheader("Paso 2: Selecciona Filtro de Estado")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✓ Solo Activos", key="activos", use_container_width=True, help="Estado = A"):
            st.session_state.estado = "activos"
    
    with col2:
        if st.button("◆ Todas", key="todas", use_container_width=True, help="Incluye inactivas"):
            st.session_state.estado = "todas"
    
    if st.session_state.estado:
        filtro_texto = "SOLO ACTIVOS" if st.session_state.estado == "activos" else "TODAS (incluye inactivas)"
        st.success(f"✓ Filtro: {filtro_texto}")
        
        # Paso 3: Cargar ZIP
        st.subheader("Paso 3: Carga el archivo ZIP")
        uploaded_file = st.file_uploader("Selecciona el ZIP", type=["zip"], key=f"uploader_{st.session_state.pais}_{st.session_state.estado}")
        
        if uploaded_file is not None:
            if not st.session_state.procesado:
                with st.spinner("📦 Descomprimiendo y procesando archivo..."):
                    try:
                        # Extrae ZIP en memoria
                        temp_dir = "temp_extract"
                        if os.path.exists(temp_dir):
                            shutil.rmtree(temp_dir)
                        os.makedirs(temp_dir)
                        
                        with zipfile.ZipFile(uploaded_file) as zip_ref:
                            zip_ref.extractall(temp_dir)
                        
                        # Encuentra Posición.csv
                        csv_file = None
                        for root, dirs, files in os.walk(temp_dir):
                            for file in files:
                                if file.lower() == "posición.csv" or file.lower() == "posicion.csv":
                                    csv_file = os.path.join(root, file)
                                    break
                        
                        if not csv_file:
                            st.error("❌ No se encontró Posición.csv en el ZIP")
                        else:
                            # Procesa el CSV
                            posiciones = {}
                            contador = 0
                            descartadas = 0
                            fieldnames = None
                            
                            with open(csv_file, 'r', encoding='utf-8-sig') as f_in:
                                next(f_in)
                                reader = csv.DictReader(f_in)
                                fieldnames = reader.fieldnames
                                
                                for row in reader:
                                    contador += 1
                                    
                                    # ===== FILTRO 1: Estado (A/I) =====
                                    estado = None
                                    for key in reader.fieldnames:
                                        if key.startswith("Estado"):
                                            estado = row.get(key, "").strip().strip('"').strip()
                                            break
                                    
                                    # Si es "activos", solo incluir Estado = "A"
                                    # Si es "todas", incluir TODO (sin filtrar por estado)
                                    if st.session_state.estado == "activos":
                                        if estado != "A":
                                            descartadas += 1
                                            continue
                                    # Si es "todas", no filtra por estado, continúa
                                    
                                    # ===== FILTRO 2: País/Empresa =====
                                    empresa_id = row.get("Razón social.ID de razón social", "").strip().strip('"').strip()
                                    
                                    if st.session_state.pais == "Peru":
                                        # PERÚ: mantener SOLO 2301 y 2101
                                        if empresa_id not in ["2301", "2101"]:
                                            descartadas += 1
                                            continue
                                    else:  # Chile
                                        # CHILE: excluir 2301 y 2101
                                        if empresa_id in ["2301", "2101"]:
                                            descartadas += 1
                                            continue
                                    
                                    # ===== AGRUPACIÓN: Obtiene ID de posición y fecha =====
                                    id_posicion = row.get("ID de posición", "").strip()
                                    fecha_str = row.get("Efectivo a partir del", "").strip()
                                    
                                    if not id_posicion:
                                        continue
                                    
                                    # Parsea fecha
                                    try:
                                        fecha = datetime.strptime(fecha_str, "%d/%m/%Y")
                                    except:
                                        continue
                                    
                                    # Guarda solo la fecha más reciente por posición
                                    if id_posicion not in posiciones:
                                        posiciones[id_posicion] = (fecha, row)
                                    else:
                                        fecha_existente, row_existente = posiciones[id_posicion]
                                        if fecha > fecha_existente:
                                            posiciones[id_posicion] = (fecha, row)
                            
                            # ===== MAPEO DIRECTO DE ENCABEZADOS =====
                            mapeo_encabezados = {
                                "Operadores admitidos: Delimit, Clear y Delete": "GrupoCodigo.[OPERATOR]",
                                "ID de posición": "code",
                                "Inglés norteamericano": "GrupoCodigo.externalName.en_US",
                                "Valor predeterminado": "GrupoCodigo.externalName.defaultValue",
                                "Inglés (DEPURAR)": "GrupoCodigo.externalName.en_DEBUG",
                                "Español (España)": "GrupoCodigo.externalName.es_ES",
                                "Estado(Valid Values : A/I   A for Activo  I for Inactivo  )": "GrupoCodigo.effectiveStatus",
                                "Efectivo a partir del": "GrupoCodigo.effectiveStartDate",
                                "Criticidad": "GrupoCodigo.criticality",
                                "Titular de la posición": "GrupoCodigo.incumbent",
                                "Valor de lista desplegable.Código externo": "GrupoCodigo.changeReason.externalCode",
                                "Nombre de función del cargo": "GrupoCodigo.jobTitle",
                                "Función del cargo.Código de función del cargo": "GrupoCodigo.jobCode.externalCode",
                                "payGrade.externalCode": "GrupoCodigo.payGrade.externalCode",
                                "Cobertura del puesto": "GrupoCodigo.targetFTE",
                                "Vacante(Valid Values : TRUE/FALSE)": "GrupoCodigo.vacant",
                                "Razón social.ID de razón social": "GrupoCodigo.company.externalCode",
                                "Unidad de negocio.Código de unidad de negocio": "GrupoCodigo.businessUnit.externalCode",
                                "División.Código de división": "GrupoCodigo.division.externalCode",
                                "Departamento.Código de departamento": "GrupoCodigo.department.externalCode",
                                "location.externalCode": "GrupoCodigo.location.externalCode",
                                "Centro de costo.Código de centro de costo": "GrupoCodigo.costCenter.externalCode",
                                "Múltiples ocupantes(Valid Values : TRUE/FALSE)": "GrupoCodigo.multipleIncumbentsAllowed",
                                "Horas semanales contractuales": "GrupoCodigo.standardHours",
                                "payRange.externalCode": "GrupoCodigo.payRange.externalCode",
                                "Punto mínimo": "GrupoCodigo.cust_min",
                                "Punto medio": "GrupoCodigo.cust_mid",
                                "Punto máximo": "GrupoCodigo.cust_max",
                                "Texto breve de posición": "GrupoCodigo.cust_short",
                                "Sujeto a marcación(Valid Values : TRUE/FALSE)": "GrupoCodigo.cust_isShiftEmployee",
                                "Días laborables por semana": "GrupoCodigo.cust_workingDaysPerWeek",
                                "Observaciones": "GrupoCodigo.cust_observaciones",
                                "Posición.Posición de nivel superior": "GrupoCodigo.parentPosition.code"
                            }
                            
                            # Crea lista de nuevos nombres en el mismo orden que fieldnames
                            nuevos_fieldnames = [mapeo_encabezados.get(field, f"GrupoCodigo.{field}") for field in fieldnames]
                            
                            # Genera CSV de salida con encabezados renombrados
                            output = io.StringIO()
                            writer = csv.DictWriter(output, fieldnames=nuevos_fieldnames)
                            writer.writeheader()
                            
                            for id_pos in sorted(posiciones.keys()):
                                fecha, row = posiciones[id_pos]
                                # Reordena los valores según los nuevos nombres
                                nueva_fila = {nuevos_fieldnames[i]: row[fieldnames[i]] for i in range(len(fieldnames))}
                                writer.writerow(nueva_fila)
                            
                            csv_content = output.getvalue()
                            
                            # Validación: asegura que hay contenido
                            if not csv_content or len(csv_content.strip()) == 0:
                                st.error("❌ Error: El archivo procesado está vacío")
                                st.session_state.procesado = False
                            else:
                                # Guarda en sesión
                                st.session_state.csv_content = csv_content
                                st.session_state.contador = contador
                                st.session_state.posiciones_count = len(posiciones)
                                st.session_state.descartadas = descartadas
                                st.session_state.filename = f"UBIC_FILTRADO_{st.session_state.pais.upper()}_{st.session_state.estado.upper()}.csv"
                                st.session_state.procesado = True
                            
                            # Limpia temporal
                            shutil.rmtree(temp_dir)
                            
                            st.rerun()
                    
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            
            # Muestra resultados si fue procesado
            if st.session_state.procesado and hasattr(st.session_state, 'csv_content') and st.session_state.csv_content:
                st.markdown("---")
                st.subheader("✓ Procesamiento Completado")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Filas", st.session_state.contador)
                with col2:
                    st.metric("Posiciones Únicas", st.session_state.posiciones_count)
                with col3:
                    st.metric("Descartadas", st.session_state.descartadas)
                
                # Botón de descarga
                st.download_button(
                    label="📥 Descargar CSV",
                    data=st.session_state.csv_content,
                    file_name=st.session_state.filename,
                    mime="text/csv",
                    use_container_width=True
                )
                
                st.markdown("---")
                
                # Botón para reiniciar
                if st.button("🔄 Procesar otro archivo", use_container_width=True):
                    st.session_state.procesado = False
                    st.session_state.pais = None
                    st.session_state.estado = None
                    st.rerun()

# Footer
st.markdown("---")
st.caption("Procesador de Posiciones - Ripley | ID: 108763")
