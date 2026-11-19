"""Style commun des graphiques Plotly du dashboard (mêmes couleurs et polices que la page)."""

import plotly.graph_objects as go

INK = "#264653"
MUTED = "#6b7785"
TEAL = "#2A9D8F"
SAND = "#E9C46A"
ORANGE = "#F4A261"
CORAL = "#E76F51"
LINE = "#ECE5DA"
SEGMENT_COLORS = {
    "Grands hubs congestionnés": CORAL,
    "Aéroports régionaux perturbés": "#E0A93B",
    "Aéroports fiables": TEAL,
    "Vols courts et ponctuels": INK,
}


def styled(fig: go.Figure, height: int = 420) -> go.Figure:
    fig.update_layout(
        template="plotly_white", height=height, paper_bgcolor="white", plot_bgcolor="white",
        font={"family": "DM Sans, Arial, sans-serif", "color": INK, "size": 13},
        title_font={"family": "Poppins, Arial, sans-serif", "size": 17},
        margin={"l": 10, "r": 10, "t": 60, "b": 10},
        legend={"orientation": "h", "y": 1.08, "x": 0, "title": None},
        hoverlabel={"bgcolor": "white", "font_family": "DM Sans, Arial, sans-serif"},
    )
    fig.update_xaxes(gridcolor=LINE, zerolinecolor=LINE)
    fig.update_yaxes(gridcolor=LINE, zerolinecolor=LINE)
    return fig
