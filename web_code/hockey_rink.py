import streamlit as st
import plotly.graph_objects as go
from PIL import Image

# Funkcja do rysowania boiska hokejowego
def draw_hockey_rink():
    fig = go.Figure()
    pyLogo = Image.open("./pages/shirts/Boston/shirt.jpg")
    # Boisko
    fig.add_shape(type="rect", x0=0, y0=0, x1=106, y1=60,
                  line=dict(color="gray", width=5),
                  fillcolor="whitesmoke", layer="below")

    # Linia środkowa
    fig.add_shape(type="line", x0=53, y0=0, x1=53, y1=60,
                  line=dict(color="red", width=3))

    # Linie niebieskie
    fig.add_shape(type="line", x0=30.5, y0=0, x1=30.5, y1=60,
                  line=dict(color="blue", width=3))
    fig.add_shape(type="line", x0=75.5, y0=0, x1=75.5, y1=60,
                  line=dict(color="blue", width=3))

    # Koło na środku
    fig.add_shape(type="circle", x0=43, y0=20, x1=63, y1=40,
                  line=dict(color="blue", width=3))

    # Punkt centralny
    fig.add_shape(type="circle", x0=52.4, y0=29.4, x1=53.6, y1=30.6,
                  fillcolor="red", line=dict(color="red"))

    # Koła obronne
    for x, y in [(10, 10), (10, 50), (96, 10), (96, 50)]:
        fig.add_shape(type="circle", x0=x-8, y0=y-8, x1=x+8, y1=y+8,
                      line=dict(color="red", width=2))

    # Punkty bramkowe
    for x, y in [(18, 15), (18, 45), (88, 15), (88, 45)]:
        fig.add_shape(type="circle", x0=x-0.25, y0=y-0.25, x1=x+0.25, y1=y+0.25,
                      fillcolor="red", line=dict(color="red"))

    # Bramki
    fig.add_shape(type="rect", x0=0, y0=23.5, x1=2, y1=36.5,
                  line=dict(color="red", width=5), fillcolor="white")
    fig.add_shape(type="rect", x0=104, y0=23.5, x1=106, y1=36.5,
                  line=dict(color="red", width=5), fillcolor="white")

    # Dodanie koszulek zawodników
    fig.add_layout_image(
        source=pyLogo,
        x=20, y=50,  # Pozycja na boisku (x, y)
        xref="x", yref="y",
        sizex=6, sizey=6,  # Rozmiar koszulki
        xanchor="center", yanchor="middle",
        layer="above"
    )
    fig.add_layout_image(
        source=pyLogo,
        x=86, y=10,
        xref="x", yref="y",
        sizex=6, sizey=6,
        xanchor="center", yanchor="middle",
        layer="above"
    )

    # Ustawienia osi
    fig.update_xaxes(range=[0, 106], showgrid=False, zeroline=False, visible=False)
    fig.update_yaxes(range=[0, 60], showgrid=False, zeroline=False, visible=False)

    # Ustawienia wykresu
    fig.update_layout(
        width=1060,
        height=600,
        showlegend=False,
        plot_bgcolor="whitesmoke",
        margin=dict(l=0, r=0, t=0, b=0)
    )

    return fig

# Streamlit UI
