import streamlit as st
from neo4j import GraphDatabase
import pandas as pd
import plotly.graph_objs as go
from neo4j.exceptions import CypherSyntaxError

# Neo4j connection setup
URI = "neo4j+s://cc7e7431.databases.neo4j.io"
USERNAME = "neo4j"
PASSWORD = "6VhDjKoz1Gkh4qT4DMJAy_qQ6wsI2bRajAJUwOTFkAY"

driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

# Custom dark style
st.set_page_config(page_title="Football Graph Database", layout="wide")

st.markdown(
    """
    <style>
        body {
            background-color: #0b1a38;
            color: white;
        }
        .main {
            background-color: #0b1a38;
        }
        header, footer, .css-18e3th9 {
            background-color: #0b1a38;
        }
        h1, h2, h3, h4 {
            color: white;
        }
        .stTextInput>div>div>input {
            background-color: #0b1a38;
            color: white;
        }
        .stButton>button {
            background-color: #0057b8;
            color: white;
        }
        .stDataFrame {
            background-color: #0b1a38;
            color: white;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Title
st.title("🏆 Football Graph Database")

# Query input
query = st.text_area("Enter Cypher query:", height=150)

def record_to_dict(record):
    result = {}
    for key in record.keys():
        item = record[key]
        if hasattr(item, "id") and hasattr(item, "labels"):
            # Node: show label and 'name' property or id
            label = list(item.labels)[0] if item.labels else "Node"
            name = item.get("name", f"{label} {item.id}")
            result[key] = f"{label}: {name}"
        elif hasattr(item, "type") and hasattr(item, "start_node") and hasattr(item, "end_node"):
            # Relationship: show type and connected node ids
            result[key] = f":{item.type} ({item.start_node.id} → {item.end_node.id})"
        else:
            # Other types (primitive)
            result[key] = item
    return result

# Run button
if st.button("Run Query"):
    if query.strip() == "":
        st.warning("Please enter a Cypher query.")
    else:
        with driver.session() as session:
            try:
                result = session.run(query)
                records = list(result)

                if not records:
                    st.info("Query returned no results.")
                else:
                    # Use safe conversion for table with nodes and relationships
                    df = pd.DataFrame([record_to_dict(r) for r in records])
                    st.subheader("📋 Query Results (Table)")
                    st.dataframe(df)

                    # Graph visualization
                    st.subheader("🌐 Query Results (Graph Visualization)")

                    nodes = {}
                    edges = []

                    for record in records:
                        for key in record.keys():
                            item = record[key]

                            # Process nodes
                            if hasattr(item, "id") and hasattr(item, "labels"):
                                node_id = item.id
                                label = list(item.labels)[0] if item.labels else "Node"
                                name = item.get("name", f"{label} {node_id}")
                                nodes[node_id] = {
                                    "label": label,
                                    "name": name,
                                    "color": f"#{hash(label) & 0xFFFFFF:06x}"
                                }
                            # Process relationships
                            elif hasattr(item, "type") and hasattr(item, "start_node") and hasattr(item, "end_node"):
                                start_id = item.start_node.id
                                end_id = item.end_node.id
                                rel_type = item.type
                                edges.append({
                                    "start": start_id,
                                    "end": end_id,
                                    "type": rel_type
                                })

                    if nodes:
                        # Layout nodes in a circle for better spacing
                        import math
                        n_nodes = len(nodes)
                        angle_step = 2 * math.pi / n_nodes if n_nodes else 1
                        pos = {}
                        radius = 10
                        for i, node_id in enumerate(nodes.keys()):
                            angle = i * angle_step
                            pos[node_id] = (radius * math.cos(angle), radius * math.sin(angle))

                        edge_x, edge_y, edge_texts = [], [], []
                        for edge in edges:
                            x0, y0 = pos[edge["start"]]
                            x1, y1 = pos[edge["end"]]
                            edge_x += [x0, x1, None]
                            edge_y += [y0, y1, None]
                            edge_texts.append(edge["type"])

                        edge_trace = go.Scatter(
                            x=edge_x, y=edge_y,
                            line=dict(width=1, color='#888'),
                            hoverinfo='none',
                            mode='lines'
                        )

                        node_x, node_y, node_text, node_color = [], [], [], []
                        for node_id, props in nodes.items():
                            x, y = pos[node_id]
                            node_x.append(x)
                            node_y.append(y)
                            node_text.append(f"{props['label']}: {props['name']}")
                            node_color.append(props["color"])

                        node_trace = go.Scatter(
                            x=node_x, y=node_y,
                            mode='markers+text',
                            text=[nodes[nid]["name"] for nid in nodes],
                            textposition="bottom center",
                            hoverinfo='text',
                            marker=dict(
                                showscale=False,
                                color=node_color,
                                size=25,
                                line=dict(width=2, color='white')
                            )
                        )

                        # Create arrows for edges with labels
                        annotations = []
                        for edge in edges:
                            x0, y0 = pos[edge["start"]]
                            x1, y1 = pos[edge["end"]]

                            # Arrow annotation with label (relationship type)
                            annotations.append(
                                dict(
                                    ax=x0,
                                    ay=y0,
                                    x=x1,
                                    y=y1,
                                    xref='x',
                                    yref='y',
                                    axref='x',
                                    ayref='y',
                                    showarrow=True,
                                    arrowsize=2,
                                    arrowwidth=1.5,
                                    arrowhead=3,
                                    standoff=10,
                                    startstandoff=5,
                                    arrowcolor="#888",
                                    text=f":{edge['type']}",
                                    font=dict(color='yellow', size=12),
                                    align="center"
                                )
                            )

                        fig = go.Figure(data=[edge_trace, node_trace],
                                        layout=go.Layout(
                                            title='<br>Graph View of Results',
                                            titlefont_size=20,
                                            showlegend=False,
                                            hovermode='closest',
                                            margin=dict(b=20, l=5, r=5, t=50),
                                            paper_bgcolor="#0b1a38",
                                            plot_bgcolor="#0b1a38",
                                            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                            annotations=annotations,
                                            font=dict(color='white')
                                        ))
                        st.plotly_chart(fig, use_container_width=True)

                    else:
                        st.warning("No graph elements to visualize.")

            except CypherSyntaxError as e:
                st.error(f"Cypher syntax error: {e}")
            except Exception as e:
                st.error(f"Query failed: {e}")
