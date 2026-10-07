import html
import networkx as nx
import pandas as pd
import plotly.graph_objects as go

COLORS={'PENDING':'#96a5b4','RUNNING':'#e8aa39','COMPLETED':'#19a68c','WARNING':'#e8aa39','FAILED':'#e66470'}

def dag_figure(states,edges):
    graph=nx.DiGraph(); graph.add_nodes_from(states); graph.add_edges_from(edges)
    if not nx.is_directed_acyclic_graph(graph): raise ValueError('Cycle in displayed DAG')
    positions={}
    for x,layer in enumerate(nx.topological_generations(graph)):
        nodes=list(layer)
        for i,n in enumerate(nodes): positions[n]=(x,i-(len(nodes)-1)/2)
    figure=go.Figure()
    for a,b in edges:
        x,y=positions[b]; ax,ay=positions[a]
        figure.add_annotation(x=x,y=y,ax=ax,ay=ay,xref='x',yref='y',axref='x',ayref='y',showarrow=True,arrowhead=3,arrowcolor='#c1cdd9',arrowsize=1.2)
    hover=[]
    for node,state in states.items():
        hover.append(html.escape(node)+'<br>'+html.escape(state['status'])+f"<br>{state['duration_seconds']:.3f}s"+'<br>Requires: '+html.escape(', '.join(state['dependencies']) or 'None')+'<br>'+html.escape(state.get('explanation','')))
    figure.add_trace(go.Scatter(x=[positions[n][0] for n in states],y=[positions[n][1] for n in states],mode='markers+text',
        marker={'size':26,'color':[COLORS[s['status']] for s in states.values()]},
        text=[html.escape(n).replace(' · ','<br>')+'<br>'+s['status'] for n,s in states.items()],textposition='top center',
        customdata=list(states),hovertext=hover,hoverinfo='text'))
    figure.update_layout(height=430,showlegend=False,margin={'l':45,'r':45,'t':75,'b':20},xaxis={'visible':False,'range':[-.4,max(x for x,y in positions.values())+.4]},yaxis={'visible':False,'range':[-1.2,1.4]},paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')
    return figure

def similarity_figure(matrix):
    fig=go.Figure(go.Heatmap(z=matrix.values,x=list(matrix.columns),y=list(matrix.index),zmin=0,zmax=1,colorscale='Teal',text=matrix.values,texttemplate='%{text:.0%}',hovertemplate='%{y} ↔ %{x}: %{z:.3f}<extra></extra>'))
    fig.update_layout(height=430,margin={'t':20,'b':20}); return fig

def quality_figure(before,after):
    metrics=['completeness','uniqueness','validity','type_consistency','categorical_consistency','format_consistency']
    fig=go.Figure()
    for label,data,color in [('Before',before,'#a4b6ca'),('After',after,'#19a68c')]:
        fig.add_bar(name=label,x=[x.replace('_',' ').title() for x in metrics],y=[data[x] for x in metrics],marker_color=color)
    fig.update_layout(barmode='group',yaxis={'range':[0,100],'title':'Percent'},height=360,margin={'t':20}); return fig

def timeline_figure(states):
    fig=go.Figure()
    for name,s in states.items():
        if s['start_offset_seconds'] is not None:
            fig.add_bar(y=[name],x=[max(.0001,s['end_offset_seconds']-s['start_offset_seconds'])],base=[s['start_offset_seconds']],orientation='h',marker_color=COLORS[s['status']],name=name)
    fig.update_layout(height=360,showlegend=False,xaxis_title='Seconds since pipeline start',barmode='overlay',margin={'t':20}); return fig
