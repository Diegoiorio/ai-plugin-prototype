"""Costruzione di query SQL sicure a partire da un piano strutturato.

Responsabilita:
- Validare tabelle/campi/operatori/trasformazioni contro `SAFE_DB_SCHEMA`.
- Tradurre un piano JSON (prodotto dal layer AI) in SQLAlchemy `text` parametrizzato.
- Restituire metadati colonne e configurazione chart coerenti con la query.

Ruolo nel flusso applicativo:
- `main.py` invoca `build_safe_query` prima dell'esecuzione su database.
- Questo modulo rappresenta il confine tra output AI e SQL realmente eseguibile.

Dipendenze principali:
- `fastapi.HTTPException` per errori di validazione dominio.
- `sqlalchemy.text` per query raw parametrizzate.
- `ai_schema.SAFE_DB_SCHEMA` come whitelist centrale.

Cosa NON fa questo modulo:
- Non chiama modelli AI.
- Non espone endpoint API.
- Non applica logiche di business fuori dal piano query.
"""

from typing import Any
from fastapi import HTTPException
from sqlalchemy import text

from ai_schema import SAFE_DB_SCHEMA


TABLE_ALIASES = {
    "opportunities": "o",
    "customers": "c",
    "users": "u",
}

ALLOWED_AGGREGATIONS = {
    "sum",
    "avg",
    "count",
    "count_distinct",
    "min",
    "max",
}

ALLOWED_OPERATORS = {
    "=",
    "!=",
    ">",
    ">=",
    "<",
    "<=",
    "in",
}

ALLOWED_TRANSFORMS = {
    "month",
    "year",
}

ALLOWED_DIRECTIONS = {
    "asc",
    "desc",
}


def get_field_meta(table: str, field: str) -> dict[str, Any]:
    """Recupera i metadati di un campo consentito dallo schema safe.

    Args:
        table: Nome tabella logica.
        field: Nome colonna nella tabella.

    Returns:
        Dizionario metadati del campo (`type`, `description`, ...).

    Raises:
        HTTPException: Se tabella o campo non sono presenti nella whitelist.
    """
    try:
        return SAFE_DB_SCHEMA["tables"][table]["fields"][field]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Campo non consentito: {table}.{field}"
        )


def validate_table(table: str):
    """Verifica che la tabella richiesta sia presente nello schema consentito."""
    if table not in SAFE_DB_SCHEMA["tables"]:
        raise HTTPException(
            status_code=400,
            detail=f"Tabella non consentita: {table}"
        )


def validate_relation(base_table: str, join_table: str):
    """Convalida che la relazione tra tabella base e join sia permessa.

    Returns:
        La relazione trovata nello schema safe.

    Raises:
        HTTPException: Se non esiste una relazione ammessa tra le due tabelle.
    """
    for relation in SAFE_DB_SCHEMA["relations"]:
        valid_forward = (
            relation["from_table"] == base_table
            and relation["to_table"] == join_table
        )
        valid_reverse = (
            relation["to_table"] == base_table
            and relation["from_table"] == join_table
        )

        if valid_forward or valid_reverse:
            return relation

    raise HTTPException(
        status_code=400,
        detail=f"Relazione non consentita: {base_table} -> {join_table}"
    )


def sql_field(table: str, field: str, transform: str | None = None) -> str:
    """Converte una coppia tabella/campo in espressione SQL sicura.

    Args:
        table: Tabella consentita.
        field: Campo consentito.
        transform: Trasformazione opzionale (`month`, `year`).

    Returns:
        Frammento SQL pronto per SELECT/GROUP BY.
    """
    validate_table(table)
    get_field_meta(table, field)

    alias = TABLE_ALIASES[table]
    raw_field = f"{alias}.{field}"

    if transform is None:
        return raw_field

    if transform not in ALLOWED_TRANSFORMS:
        raise HTTPException(
            status_code=400,
            detail=f"Trasformazione non consentita: {transform}"
        )

    field_type = get_field_meta(table, field)["type"]

    if field_type != "temporal":
        raise HTTPException(
            status_code=400,
            detail=f"La trasformazione {transform} è consentita solo su campi temporali."
        )

    if transform == "month":
        return f"TO_CHAR(DATE_TRUNC('month', {raw_field}), 'YYYY-MM')"

    if transform == "year":
        return f"TO_CHAR(DATE_TRUNC('year', {raw_field}), 'YYYY')"

    raise HTTPException(status_code=400, detail="Trasformazione non valida.")


def build_select_item(item: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Costruisce una select expression e i metadati della colonna risultante.

    Args:
        item: Definizione di select del piano AI.

    Returns:
        Tupla: (frammento SQL aliasato, metadati colonna per la risposta API).
    """
    table = item.get("table")
    field = item.get("field")
    alias = item.get("alias")
    transform = item.get("transform")
    aggregation = item.get("aggregation")

    if not table or not field or not alias:
        raise HTTPException(
            status_code=400,
            detail="Ogni campo select deve avere table, field e alias."
        )

    validate_table(table)
    field_meta = get_field_meta(table, field)

    base_expr = sql_field(table, field, transform)

    if aggregation:
        if aggregation not in ALLOWED_AGGREGATIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Aggregazione non consentita: {aggregation}"
            )

        if aggregation == "count":
            expr = f"COUNT({base_expr})"
            semantic_type = "number"
        elif aggregation == "count_distinct":
            expr = f"COUNT(DISTINCT {base_expr})"
            semantic_type = "number"
        else:
            if field_meta["type"] != "number":
                raise HTTPException(
                    status_code=400,
                    detail=f"L'aggregazione {aggregation} richiede un campo numerico."
                )
            expr = f"{aggregation.upper()}({base_expr})"
            semantic_type = "number"
    else:
        expr = base_expr
        semantic_type = field_meta["type"]

    column = {
        "key": alias,
        "label": item.get("label", alias),
        "type": semantic_type,
    }

    return f"{expr} AS {alias}", column


def build_filter_item(item: dict[str, Any], index: int) -> tuple[str, dict[str, Any]]:
    """Costruisce una clausola WHERE parametrizzata e i relativi parametri.

    Args:
        item: Filtro del piano query.
        index: Indice usato per generare un nome parametro stabile.

    Returns:
        Tupla: (frammento SQL filtro, dizionario parametri bind).
    """
    table = item.get("table")
    field = item.get("field")
    operator = item.get("operator")
    value = item.get("value")

    if not table or not field or not operator:
        raise HTTPException(
            status_code=400,
            detail="Ogni filtro deve avere table, field e operator."
        )

    validate_table(table)
    get_field_meta(table, field)

    if operator not in ALLOWED_OPERATORS:
        raise HTTPException(
            status_code=400,
            detail=f"Operatore non consentito: {operator}"
        )

    param_name = f"filter_{index}"
    field_sql = sql_field(table, field)

    if operator == "in":
        if not isinstance(value, list):
            raise HTTPException(
                status_code=400,
                detail="L'operatore IN richiede una lista di valori."
            )
        return f"{field_sql} = ANY(:{param_name})", {param_name: value}

    return f"{field_sql} {operator} :{param_name}", {param_name: value}


def build_join_sql(base_table: str, joins: list[str]) -> str:
    """Genera le clausole LEFT JOIN consentite dallo schema safe.

    Args:
        base_table: Tabella principale del FROM.
        joins: Elenco tabelle da collegare.

    Returns:
        Stringa SQL contenente zero o piu join.
    """
    join_parts = []

    for join_table in joins:
        validate_table(join_table)
        relation = validate_relation(base_table, join_table)

        from_alias = TABLE_ALIASES[relation["from_table"]]
        to_alias = TABLE_ALIASES[relation["to_table"]]

        if relation["from_table"] == base_table:
            join_parts.append(
                f"LEFT JOIN {relation['to_table']} {to_alias} "
                f"ON {from_alias}.{relation['from_field']} = {to_alias}.{relation['to_field']}"
            )
        else:
            join_parts.append(
                f"LEFT JOIN {relation['from_table']} {from_alias} "
                f"ON {from_alias}.{relation['from_field']} = {to_alias}.{relation['to_field']}"
            )

    return "\n".join(join_parts)


def build_safe_query(plan: dict[str, Any]) -> tuple[Any, list[dict[str, Any]], dict[str, Any]]:
    """Traduce un piano AI in query SQL sicura e metadati risposta.

    Args:
        plan: Piano strutturato con base_table/select/filters/group/order/chart.

    Returns:
        Tupla con:
        - query SQLAlchemy `text` parametrizzata;
        - lista metadati colonne della tabella risposta;
        - parametri bind da passare a `db.execute`;
        - metadati risposta (`title`, `description`, `chart`).

    Raises:
        HTTPException: Se il piano contiene elementi non ammessi o incoerenti.
    """
    base_table = plan.get("base_table")
    validate_table(base_table)

    base_alias = TABLE_ALIASES[base_table]

    joins = plan.get("joins", [])
    if joins is None:
        joins = []

    select_items = plan.get("select", [])
    if not select_items:
        raise HTTPException(
            status_code=400,
            detail="La richiesta non contiene campi da selezionare."
        )

    select_sql_parts = []
    columns = []

    for item in select_items:
        select_sql, column = build_select_item(item)
        select_sql_parts.append(select_sql)
        columns.append(column)

    where_parts = []
    params = {}

    for index, filter_item in enumerate(plan.get("filters", []) or []):
        where_sql, where_params = build_filter_item(filter_item, index)
        where_parts.append(where_sql)
        params.update(where_params)

    group_by_parts = []

    for item in plan.get("group_by", []) or []:
        table = item.get("table")
        field = item.get("field")
        transform = item.get("transform")
        group_by_parts.append(sql_field(table, field, transform))

    order_by_parts = []

    for item in plan.get("order_by", []) or []:
        alias = item.get("field")
        direction = item.get("direction", "asc")

        valid_aliases = [column["key"] for column in columns]

        if alias not in valid_aliases:
            raise HTTPException(
                status_code=400,
                detail=f"Ordinamento non consentito su campo: {alias}"
            )

        if direction not in ALLOWED_DIRECTIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Direzione ordinamento non valida: {direction}"
            )

        order_by_parts.append(f"{alias} {direction.upper()}")

    limit = plan.get("limit", 100)

    if not isinstance(limit, int) or limit < 1 or limit > 500:
        limit = 100

    sql = f"""
        SELECT
            {", ".join(select_sql_parts)}
        FROM {base_table} {base_alias}
        {build_join_sql(base_table, joins)}
    """

    if where_parts:
        sql += "\nWHERE " + " AND ".join(where_parts)

    if group_by_parts:
        sql += "\nGROUP BY " + ", ".join(group_by_parts)

    if order_by_parts:
        sql += "\nORDER BY " + ", ".join(order_by_parts)

    sql += "\nLIMIT :limit"
    params["limit"] = limit

    chart = plan.get("chart", {}) or {}

    response_meta = {
        "title": plan.get("title", "Analisi dati CRM"),
        "description": plan.get("description", "Analisi generata dalla richiesta utente."),
        "chart": chart,
    }

    return text(sql), columns, params, response_meta