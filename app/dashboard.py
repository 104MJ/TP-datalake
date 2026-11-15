import streamlit as st
import plotly.express as px  # noqa: F401
from pyspark.sql import SparkSession

st.set_page_config(page_title="Lakehouse Analytics", layout="wide")
st.title("Explorateur Data Lakehouse (HDFS + Delta Lake)")


@st.cache_resource
def get_spark():
    return (
        SparkSession.builder
        .appName("StreamlitGoldReader")
        .config("spark.driver.memory", "512m")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )


@st.cache_data(ttl=60)
def load_gold_table(hdfs_path: str):
    spark = get_spark()
    return spark.read.format("delta").load(hdfs_path).toPandas()


st.info(
    "Cluster HDFS connecté (`hdfs://namenode:9000`). "
    "Alimentez vos tables Delta dans `/lakehouse/gold/` depuis JupyterLab pour afficher vos analyses ici."
)

with st.expander("Exemple d'intégration d'une requête expliquée (attendu pour le projet)"):
    st.code(
        """
SELECT category,
       COUNT(*) AS total_orders,
       PERCENTILE_APPROX(delivery_days, 0.5) AS median_delivery_days
FROM delta.`/lakehouse/silver/orders`
GROUP BY category
ORDER BY total_orders DESC;
        """,
        language="sql",
    )
    st.markdown(
        "**Justification statistique :** Utilisation de la médiane plutôt que de la moyenne "
        "pour neutraliser les retards logistiques extrêmes."
    )

# ==============================================================================
# TODO (TP Jours 3 & 4) — À COMPLÉTER PAR LES ÉTUDIANTS
# ==============================================================================
# Une fois vos tables Gold générées sur HDFS dans `/lakehouse/gold/` :
# 1. Chargez vos tables via `load_gold_table("/lakehouse/gold/kpi_categories")`,
#    `load_gold_table("/lakehouse/gold/kpi_monthly")`, `load_gold_table("/lakehouse/gold/customer_rfm")`, etc.
# 2. Construisez vos visualisations interactives avec `plotly.express` (`px.bar`, `px.scatter`, `px.line`, `px.pie`).
# 3. Pour chaque indicateur restitué, ajoutez un bloc `st.expander(...)` présentant
#    la requête SQL exécutée et sa justification statistique (médiane vs moyenne, IQR, Pareto, RFM).
