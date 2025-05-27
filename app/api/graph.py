# app/api/graph.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from falkordb import FalkorDB
from app.config import FALKORDB_HOST, FALKORDB_PORT, KG_NAME
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/graph")
async def get_graph():
    try:
        fdb = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
        g = fdb.select_graph(KG_NAME)
        query = """
        MATCH (n)-[r]->(m)
        RETURN n, r, m
        LIMIT 100
        """
        result = g.query(query)
        nodes = []
        edges = []

        for record in result.result_set:
            n = record[0]
            r = record[1]
            m = record[2]

            nodes.append({
                "id": n.id,
                "label": n.labels[0] if n.labels else 'Node',
                "properties": n.properties
            })
            nodes.append({
                "id": m.id,
                "label": m.labels[0] if m.labels else 'Node',
                "properties": m.properties
            })
            # Check if r is dict or object and get relationshipType accordingly
            rel_type = None
            if isinstance(r, dict):
                rel_type = r.get("relationshipType", "RELATED")
            else:
                rel_type = getattr(r, "relationshipType", "RELATED")

            edges.append({
                "source": n.id,
                "target": m.id,
                "type": rel_type
            })

        unique_nodes = {node['id']: node for node in nodes}.values()

        return JSONResponse(content={
            "nodes": list(unique_nodes),
            "edges": edges
        })

    except Exception as e:
        logger.error(f"Failed to fetch graph data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch graph data")
