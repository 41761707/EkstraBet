import streamlit as st
import plotly.graph_objects as go
from PIL import Image
import numpy as np

# Funkcja do rysowania boiska hokejowego

def generate_half_circle(x_center, y_center, radius, direction="right"):
    if direction == "right":
        start_angle = 0
        end_angle = 180
    else:
        start_angle = 180
        end_angle = 360

    circle = go.Scatter(
        x=[x_center + radius * np.cos(np.deg2rad(i)) for i in range(start_angle, end_angle + 1)],
        y=[y_center + radius * np.sin(np.deg2rad(i)) for i in range(start_angle, end_angle + 1)],
        mode="lines",
        line=dict(color="blue", width=3),
        fill="toself",
    )

    return circle

def draw_hockey_rink():
    fig = go.Figure()
    team_shirt = Image.open("./pages/shirts/Boston_Bruins.jpg")
    # Boisko
    fig.add_shape(type="rect", x0=0, y0=0, x1=40, y1=60,
                  line=dict(color="white", width=5),
                  fillcolor="white", layer="below")

    # Linia środkowa
    fig.add_shape(type="line", x0=0, y0=30, x1=40, y1=30,
                  line=dict(color="red", width=5), layer="below")

    # Linie niebieskie
    fig.add_shape(type="line", x0=0, y0=20, x1=40, y1=20,
                  line=dict(color="blue", width=3), layer="below")
    fig.add_shape(type="line", x0=0, y0=40, x1=40, y1=40,
                  line=dict(color="blue", width=3), layer="below")
    
    #Linie bramkowe
    fig.add_shape(type="line", x0=0, y0=5, x1=40, y1=5,
                  line=dict(color="red", width=3), layer="below")
    fig.add_shape(type="line", x0=0, y0=55, x1=40, y1=55,
                  line=dict(color="red", width=3), layer="below")

    # Koło na środku
    fig.add_shape(type="circle", x0=15, y0=25, x1=25, y1=35,
                  line=dict(color="blue", width=3), layer="below")

    # Punkt centralny
    fig.add_shape(type="circle", x0=19.5, y0=29.5, x1=20.5, y1=30.5,
                  fillcolor="red", line=dict(color="red"), layer="below")

    # Koła obronne
    for x, y in [(3, 6), (29, 6), (3, 46), (29, 46)]:
        fig.add_shape(type="circle", x0=x, y0=y, x1=x+8, y1=y+8,
                      line=dict(color="red", width=2), layer="below")
        
    #Kółko w kołach obronnych
    for x, y in [(7, 10), (33, 10), (7, 50), (33, 50)]:
        fig.add_shape(type="circle", x0=x-0.25, y0=y-0.25, x1=x+0.25, y1=y+0.25,
                    fillcolor="red", line=dict(color="red"), layer="below")
        
    #Bramki 
    fig.add_trace(generate_half_circle(20, 5, 2.5, direction="right"))
    fig.add_trace(generate_half_circle(20, 55, 2.5, direction="left"))
    # Punkty bramkowe
    '''for x, y in [(18, 15), (18, 45), (88, 15), (88, 45)]:
        fig.add_shape(type="circle", x0=x-0.25, y0=y-0.25, x1=x+0.25, y1=y+0.25,
                      fillcolor="red", line=dict(color="red"))

    # Bramki
    fig.add_shape(type="rect", x0=0, y0=23.5, x1=2, y1=36.5,
                  line=dict(color="red", width=5), fillcolor="white")
    fig.add_shape(type="rect", x0=104, y0=23.5, x1=106, y1=36.5,
                  line=dict(color="red", width=5), fillcolor="white")'''

    # Dodanie koszulek zawodników
    fig.add_layout_image(
        source=team_shirt,
        x=7, y=45,  # Pozycja na boisku (x, y)
        xref="x", yref="y",
        sizex=10, sizey=10,  # Rozmiar koszulki
        xanchor="center", yanchor="middle",
        layer="above",
    )
    fig.add_annotation(
        text="Marchand B.",  # Tekst na koszulce
        x=7, y=38,  # Position below the image
        xref="x", yref="y",
        showarrow=False,
        font=dict(size=15, color="black"),
        xanchor="center"
    )
    fig.add_layout_image(
        source=team_shirt,
        x=20, y=45,  # Pozycja na boisku (x, y)
        xref="x", yref="y",
        sizex=10, sizey=10,  # Rozmiar koszulki
        xanchor="center", yanchor="middle",
        layer="above",
    )
    fig.add_annotation(
        text="Bergeron P.",  # Tekst na koszulce
        x=20, y=38,  # Position below the image
        xref="x", yref="y",
        showarrow=False,
        font=dict(size=15, color="black"),
        xanchor="center"
    )
    fig.add_layout_image(
        source=team_shirt,
        x=33, y=45,  # Pozycja na boisku (x, y)
        xref="x", yref="y",
        sizex=10, sizey=10,  # Rozmiar koszulki
        xanchor="center", yanchor="middle",
        layer="above",
    )
    fig.add_annotation(
        text="Pastrnak D.",  # Tekst na koszulce
        x=33, y=38,  # Position below the image
        xref="x", yref="y",
        showarrow=False,
        font=dict(size=15, color="black"),
        xanchor="center"
    )

    fig.add_layout_image(
        source=team_shirt,
        x=13.5, y=25,  # Pozycja na boisku (x, y)
        xref="x", yref="y",
        sizex=10, sizey=10,  # Rozmiar koszulki
        xanchor="center", yanchor="middle",
        layer="above",
    )
    fig.add_annotation(
        text="Carlo B.",  # Tekst na koszulce
        x=13.5, y=17,  # Position below the image
        xref="x", yref="y",
        showarrow=False,
        font=dict(size=15, color="black"),
        xanchor="center"
    )    
    fig.add_layout_image(
        source=team_shirt,
        x=26.5, y=25,  # Pozycja na boisku (x, y)
        xref="x", yref="y",
        sizex=10, sizey=10,  # Rozmiar koszulki
        xanchor="center", yanchor="middle",
        layer="above",
    )
    fig.add_annotation(
        text="Chara Z.",  # Tekst na koszulce
        x=26.5, y=17,  # Position below the image
        xref="x", yref="y",
        showarrow=False,
        font=dict(size=15, color="black"),
        xanchor="center"
    )    

    fig.add_layout_image(
        source=team_shirt,
        x=20, y=11,  # Pozycja na boisku (x, y)
        xref="x", yref="y",
        sizex=10, sizey=10,  # Rozmiar koszulki
        xanchor="center", yanchor="middle",
        layer="above",
    )
    fig.add_annotation(
        text="Rask T.",  # Tekst na koszulce
        x=20, y=3,  # Position below the image
        xref="x", yref="y",
        showarrow=False,
        font=dict(size=15, color="black"),
        xanchor="center"
    )   

    # Ustawienia osi
    fig.update_xaxes(range=[0, 40], showgrid=False, zeroline=False, visible=False)
    fig.update_yaxes(range=[0, 60], showgrid=False, zeroline=False, visible=False)

    # Ustawienia wykresu
    fig.update_layout(
        width=400,
        height=600,
        showlegend=False,
        plot_bgcolor="whitesmoke",
        margin=dict(l=0, r=0, t=0, b=0)
    )

    return fig

# Streamlit UI
