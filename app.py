import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from io import BytesIO

def calcular_domingo_vectorizado(semanas, anios, meses):
    # Calcular el primer lunes del año según la ISO 8601 (semana que contiene el 4 de enero)
    primer_jueves = np.array([datetime(int(a), 1, 4) for a in anios])
    primer_lunes = np.array([d - timedelta(days=d.weekday()) for d in primer_jueves])

    # Calcular el domingo de la semana dada
    fecha_domingo = np.array([l + timedelta(weeks=int(s)-1, days=6) for l, s in zip(primer_lunes, semanas)])

    # Guardar la fecha del domingo antes del ajuste
    fecha_domingo_original = fecha_domingo.copy()

    # Ajustar fecha si el domingo excede el mes dado
    ultimo_dia_mes = np.array([datetime(int(a), int(m)+1, 1) - timedelta(days=1) if m < 12 else datetime(int(a), 12, 31) for a, m in zip(anios, meses)])
    fecha_domingo = np.where(fecha_domingo > ultimo_dia_mes, ultimo_dia_mes, fecha_domingo)

    return fecha_domingo, fecha_domingo_original

def transformar_dataframe(df):
    # Definir los encabezados correctos
    diccionario_renombre = {
        "Numanio": "Numanio", "Mes": "Mes", "Semana": "Semana", "Formato": "Formato",
        "Código": "Tdacod", "Tienda": "Tienda", "Código.1": "Catcod", "Categoria": "Categoria",
        "Codbarbar": "Codbarbar", "Alterno": "Ptmcod", "Producto": "Producto",
        "Clasif Repedido": "Clasif Repedido", "Medida": "Desmed", "Venta Unidades": "Venta Unidad",
        "Venta Fardos": "Ventas Fardos", "Total de Ventas": "Ventas con IVA (Q)"
    }

    # Verificar y renombrar encabezados
    if set(diccionario_renombre.keys()).issubset(df.columns):
        df.rename(columns=diccionario_renombre, inplace=True)

    # Aplicar cálculo de domingo
    df['Fecha'], df['Fecha_Domingo_Original'] = calcular_domingo_vectorizado(df['Semana'].values, df['Numanio'].values, df['Mes'].values)

    df = df[df['Fecha'] != 'Error']

    # Expandir ventas semanales a ventas diarias
    repeticiones = np.repeat(df.index, 7)
    fechas_diarias = np.array([df.loc[i, 'Fecha'] - timedelta(days=6-j) for i in df.index for j in range(7)])

    # Crear nuevo DataFrame
    df_diario = df.loc[repeticiones].reset_index(drop=True)
    df_diario['Fecha'] = fechas_diarias

    # Filtrar filas por mes de la fecha
    df_diario['Fecha'] = pd.to_datetime(df_diario['Fecha'])
    df_diario = df_diario[df_diario['Fecha'].dt.month == df_diario['Mes']]

    # Filtrar por fecha menor al domingo original menos 6 días
    df_diario = df_diario[df_diario['Fecha'] >= df_diario['Fecha_Domingo_Original'] - timedelta(days=6)]

    # Contar días únicos por combinación
    df_diario['Dias_Unicos'] = df_diario.groupby(['Tienda','Ptmcod','Semana'])['Fecha'].transform('nunique')

    # Evitar divisiones por cero
    df_diario['Dias_Unicos'] = df_diario['Dias_Unicos'].replace(0, 1)

    # Dividir ventas por días únicos
    df_diario['Venta Unidad'] /= df_diario['Dias_Unicos']
    df_diario['Ventas con IVA (Q)'] /= df_diario['Dias_Unicos']

    df_diario.drop(columns=['Dias_Unicos'], inplace=True)

    # Eliminar registros de ventas = 0
    df_diario = df_diario[~((df_diario["Venta Unidad"] == 0) & (df_diario["Ventas con IVA (Q)"] == 0))]

    return df_diario

st.title("Procesador de Archivo CSV")

uploaded_file = st.file_uploader("Sube tu archivo CSV", type="csv")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, encoding="latin1")
        st.success("¡Archivo CSV cargado exitosamente!")

        df_transformado = transformar_dataframe(df.copy()) # Usamos una copia para no modificar el df original

        # Crear un buffer para la descarga
        buffer = BytesIO()
        df_transformado.to_csv(buffer, index=False, encoding='utf-8')
        buffer.seek(0)

        st.download_button(
            label="Descargar Archivo Transformado",
            data=buffer,
            file_name="archivo_transformado.csv",
            mime="text/csv",
        )

    except Exception as e:
        st.error(f"Ocurrió un error al procesar el archivo: {e}")


        #### cd C:\Users\Emilio\Documents\procesador_archivos
        #### streamlit run app.py