from fastapi import FastAPI, Depends, Query, Body, HTTPException
from sqlalchemy import inspect, text
from database import engine
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

@app.get("/tables")
def get_tables_and_columns():
    inspector = inspect(engine)
    tables = {}
    for table_name in inspector.get_table_names():
        columns = []
        for column in inspector.get_columns(table_name):
            columns.append({
                "nombre": column["name"],
                "tipo": str(column["type"])
            })
        
        # Detectar claves foráneas
        foreign_keys = []
        for fk in inspector.get_foreign_keys(table_name):
            foreign_keys.append({
                "column": fk["constrained_columns"],
                "referenced_table": fk["referred_table"],
                "referenced_column": fk["referred_columns"]
            })

        tables[table_name] = {"campos": columns, "foreign_keys": foreign_keys}
    
    return {"tables": tables}


@app.post("/data")
def get_filtered_data(
    table: str = Body(...),
    selected_fields: list[str] = Body(...),  # Campos seleccionados
):
    with engine.connect() as connection:
        inspector = inspect(engine)
        
        # Obtener claves foráneas salientes
        outgoing_foreign_keys = []
        for fk in inspector.get_foreign_keys(table):
            outgoing_foreign_keys.append({
                "column": fk["constrained_columns"][0],
                "referenced_table": fk["referred_table"],
                "referenced_column": fk["referred_columns"][0]
            })
        
        # Obtener claves foráneas entrantes
        incoming_foreign_keys = []
        for other_table in inspector.get_table_names():
            if other_table != table:
                for fk in inspector.get_foreign_keys(other_table):
                    if fk["referred_table"] == table:
                        incoming_foreign_keys.append({
                            "column": fk["constrained_columns"][0],
                            "table": other_table,
                            "referenced_column": fk["referred_columns"][0]
                        })
        
        # Manejar prefijos para tablas relacionadas con "empresa"
        prefixed_fields = []
        if "empresa" in table:
            for field in selected_fields:
                if "." not in field:  # Si el campo no tiene prefijo
                    prefixed_fields.append(f"{table}.{field}")
                else:
                    prefixed_fields.append(field)
        else:
            prefixed_fields = selected_fields  # Sin cambios para otras tablas

        # Crear lista de campos para el SELECT
        fields = ", ".join(prefixed_fields)
        
        # Incluir DISTINCT para evitar duplicados
        query = f"SELECT DISTINCT {fields} FROM {table}"
        
        # Agregar los LEFT JOIN automáticos para claves foráneas salientes
        for fk in outgoing_foreign_keys:
            query += f" LEFT JOIN {fk['referenced_table']} ON {table}.{fk['column']} = {fk['referenced_table']}.{fk['referenced_column']}"
        
        # Agregar los LEFT JOIN automáticos para claves foráneas entrantes
        for fk in incoming_foreign_keys:
            query += f" LEFT JOIN {fk['table']} ON {fk['table']}.{fk['column']} = {table}.{fk['referenced_column']}"
        
        # Ejecutar la consulta y obtener resultados
        try:
            result = connection.execute(text(query))
            data = [dict(row._mapping) for row in result]
            
            # Eliminar duplicados adicionales (opcional)
            unique_data = {tuple(row.items()): row for row in data}.values()
            
            return {"data": list(unique_data)}
        except Exception as e:
            print("Error en la consulta generada:", query)
            print("Detalles del error:", e)
            raise HTTPException(status_code=400, detail="Error al obtener los datos.")




@app.post("/filtered-data")
def get_filtered_data_with_filters(
    table: str = Body(...),
    filters: list[dict] = Body(...),  # Lista de filtros {nombre, valor}
    selected_fields: list[str] = Body(...),  # Campos seleccionados
):
    with engine.connect() as connection:
        inspector = inspect(engine)

        # Obtener claves foráneas salientes
        outgoing_foreign_keys = []
        for fk in inspector.get_foreign_keys(table):
            outgoing_foreign_keys.append({
                "column": fk["constrained_columns"][0],
                "referenced_table": fk["referred_table"],
                "referenced_column": fk["referred_columns"][0]
            })

        # Obtener claves foráneas entrantes
        incoming_foreign_keys = []
        for other_table in inspector.get_table_names():
            if other_table != table:
                for fk in inspector.get_foreign_keys(other_table):
                    if fk["referred_table"] == table:
                        incoming_foreign_keys.append({
                            "column": fk["constrained_columns"][0],
                            "table": other_table,
                            "referenced_column": fk["referred_columns"][0]
                        })

        # Crear lista de campos para el SELECT
        prefixed_fields = []
        if "empresa" in table:
            for field in selected_fields:
                if "." not in field:  # Si el campo no tiene prefijo
                    prefixed_fields.append(f"{table}.{field}")
                else:
                    prefixed_fields.append(field)
        else:
            prefixed_fields = selected_fields  # Sin cambios para otras tablas

        fields = ", ".join(prefixed_fields)

        # Incluir DISTINCT para evitar duplicados
        query = f"SELECT DISTINCT {fields} FROM {table}"

        # Agregar los LEFT JOIN automáticos para claves foráneas salientes
        for fk in outgoing_foreign_keys:
            query += f" LEFT JOIN {fk['referenced_table']} ON {table}.{fk['column']} = {fk['referenced_table']}.{fk['referenced_column']}"

        # Agregar los LEFT JOIN automáticos para claves foráneas entrantes
        for fk in incoming_foreign_keys:
            query += f" LEFT JOIN {fk['table']} ON {fk['table']}.{fk['column']} = {table}.{fk['referenced_column']}"

        # Manejar filtros
        filter_clauses = []
        params = {}

        for filter_item in filters:
            column = filter_item["nombre"]
            value = filter_item["valor"]

            # Verificar si la columna está en la tabla principal
            if column in [col["name"] for col in inspector.get_columns(table)]:
                filter_clauses.append(f"{table}.{column} LIKE :{column}")
                params[column] = f"%{value}%"

            # Verificar en tablas relacionadas (salientes)
            for fk in outgoing_foreign_keys:
                if column in [col["name"] for col in inspector.get_columns(fk["referenced_table"])]:
                    filter_clauses.append(f"{fk['referenced_table']}.{column} LIKE :{column}")
                    params[column] = f"%{value}%"
                    break  # Salir del bucle una vez que se encuentra el filtro

            # Verificar en tablas relacionadas (entrantes)
            for fk in incoming_foreign_keys:
                if column in [col["name"] for col in inspector.get_columns(fk["table"])]:
                    filter_clauses.append(f"{fk['table']}.{column} LIKE :{column}")
                    params[column] = f"%{value}%"
                    break  # Salir del bucle una vez que se encuentra el filtro

        # Agregar cláusulas WHERE si hay filtros
        if filter_clauses:
            query += " WHERE " + " AND ".join(filter_clauses)

        print("Consulta generada:", query)
        print("Parámetros:", params)

        # Ejecutar la consulta y obtener resultados
        try:
            result = connection.execute(text(query), params)
            data = [dict(row._mapping) for row in result]

            # Eliminar duplicados adicionales (opcional)
            unique_data = {tuple(row.items()): row for row in data}.values()

            return {"data": list(unique_data)}
        except Exception as e:
            print("Error en la consulta generada:", query)

    
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # Cambia a tu frontend si tiene un origen diferente
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)