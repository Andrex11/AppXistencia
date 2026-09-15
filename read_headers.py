import pandas as pd

try:
    df = pd.read_excel('data/horarios_empleados_particionado_x_dia_x_municipio.xlsx', header=None)
    print("Primeras 10 filas:")
    for i, row in df.head(10).iterrows():
        print(f"Fila {i}: {row.tolist()}")
except Exception as e:
    print(f"Error: {e}")
