import streamlit as st
import requests
import networkx as nx
import matplotlib.pyplot as plt

st.title("Knowledge Graph Generator UI")

# Upload PDFs
uploaded_files = st.file_uploader("Upload PDFs", accept_multiple_files=True, type=["pdf"])

if st.button("Upload and Process"):
    if not uploaded_files:
        st.warning("Please upload at least one PDF file.")
    else:
        for uploaded_file in uploaded_files:
            files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
            try:
                response = requests.post("http://127.0.0.1:8000/api/upload", files=files)
                if response.status_code == 201:
                    st.success(f"{uploaded_file.name} uploaded successfully.")
                else:
                    st.error(f"Failed to upload {uploaded_file.name}: {response.text}")
            except Exception as e:
                st.error(f"Error uploading {uploaded_file.name}: {e}")

# Show Knowledge Graph
def draw_graph(nodes, edges):
    G = nx.DiGraph()
    for node in nodes:
        G.add_node(node['id'], label=node.get('label', 'Node'))
    for edge in edges:
        G.add_edge(edge['source'], edge['target'], label=edge.get('type', 'RELATED'))
    pos = nx.spring_layout(G)
    plt.figure(figsize=(10, 6))
    nx.draw(G, pos, with_labels=True, node_size=700, node_color="skyblue", font_size=10, font_weight="bold")
    edge_labels = nx.get_edge_attributes(G, 'label')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
    st.pyplot(plt)

if st.button("Show Knowledge Graph"):
    try:
        response = requests.get("http://127.0.0.1:8000/api/graph")
        if response.status_code == 200:
            graph_data = response.json()
            draw_graph(graph_data["nodes"], graph_data["edges"])
        else:
            st.error("Failed to load graph data")
    except Exception as e:
        st.error(f"Error loading graph: {e}")

# Chat section
st.header("Chat with Knowledge Graph")
user_input = st.text_input("Enter your question:")

if st.button("Send"):
    if user_input.strip() == "":
        st.warning("Please enter a question.")
    else:
        try:
            response = requests.post(
                "http://127.0.0.1:8000/api/chat",
                json={"message": user_input}
            )
            if response.status_code == 200:
                answer = response.json().get("response", "")
                st.markdown(f"**Answer:** {answer}")
            else:
                st.error(f"Failed to get response: {response.text}")
        except Exception as e:
            st.error(f"Error during chat request: {e}")
