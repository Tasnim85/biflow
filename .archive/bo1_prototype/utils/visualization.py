import networkx as nx
import pandas as pd
import plotly.graph_objects as go

def dag_figure(plan):
    graph=nx.DiGraph(); graph.add_nodes_from(n['id'] for n in plan['nodes']); graph.add_edges_from(plan['edges'])
    if not nx.is_directed_acyclic_graph(graph): raise ValueError('Processing graph contains a cycle')
    positions={}
    for x,layer in enumerate(nx.topological_generations(graph)):
        for y,node in enumerate(layer): positions[node]=(x,-y)
    labels={n['id']:n['label'] for n in plan['nodes']}
    fig=go.Figure()
    for a,b in graph.edges:
        x0,y0=positions[a]; x1,y1=positions[b]
        fig.add_annotation(x=x1,y=y1,ax=x0,ay=y0,xref='x',yref='y',axref='x',ayref='y',showarrow=True,arrowhead=3,arrowcolor='#668ca8')
    fig.add_trace(go.Scatter(x=[positions[n][0] for n in graph],y=[positions[n][1] for n in graph],mode='markers+text',
        text=[labels[n] for n in graph],textposition='top center',hovertext=list(graph),marker=dict(size=24,color='#26b7a5')))
    fig.update_layout(height=480,showlegend=False,xaxis=dict(visible=False),yaxis=dict(visible=False),margin=dict(l=30,r=30,t=40,b=20))
    return fig

def similarity_figure(datasets,pairs):
    names=list(datasets); matrix=pd.DataFrame(0.,index=names,columns=names)
    for name in names: matrix.loc[name,name]=1.
    for p in pairs: matrix.loc[p['left'],p['right']]=matrix.loc[p['right'],p['left']]=p['score']
    return go.Figure(go.Heatmap(z=matrix.values,x=names,y=names,zmin=0,zmax=1,colorscale='Teal',text=matrix.round(2).values,texttemplate='%{text}'))
