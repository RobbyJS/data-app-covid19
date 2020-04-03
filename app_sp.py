#%%
import pandas as pd
import streamlit as st
import altair as alt
from math import ceil, floor, log10

from altair import datum
from typing import Tuple

URL_OPENCOVID19 = "https://raw.githubusercontent.com/victorvicpal/COVID19_es/master/data/final_data/dataCOVID19_es.csv"
url_pop_ccaa = "https://raw.githubusercontent.com/victorvicpal/COVID19_es/master/data/info_data/Poblaci%C3%B3nCCAA.csv"


# make title
st.title("DataViz App Covid-19 🦠")


#%% Truncate function
def truncate_10(n,up_down):
    temp = floor(log10(n))
    if up_down == "up":
        round_op = lambda x: ceil(x)
    else:
        round_op = lambda x: floor(x)

    return float(round_op(n/10**temp)*(10**temp))
#%%
@st.cache
def get_data(url) -> Tuple[pd.DataFrame]:
    """
    1 - Get data from opencovid19 repository
    2 - Transform raw data into dataframe
    3 - Returns df_covid19_fr (columns = ['date', 'type', 'nombre']) and
                df_covid19_region (columns = ['date', 'maille_nom', 'cas_confirmes', 'deces', 'delta_deces',
                                              'delta_cas_confirmes', 'fatality_rate', 'days_after_5_deaths',
                                               'days_after_50_confirmed']) 
    """
    # 1 - Get data
    data = pd.read_csv(url)
    #data = pd.read_csv(url)
    df_covid19_region = data
    
    df_covid19_region = df_covid19_region.sort_values(by=["CCAA", "fecha"])
    # create a new index based from day after 5 deaths
    df_covid19_region["days_after_5_deaths"] = (
        df_covid19_region[df_covid19_region.muertes > 5]
        .groupby("CCAA")["muertes"]
        .rank(method="first", ascending=True)
    )
    # create a new index based from day after 50 confirmed
    df_covid19_region["days_after_50_confirmed"] = (
        df_covid19_region[df_covid19_region.casos > 50]
        .groupby("CCAA")["casos"]
        .rank(method="first", ascending=True)
    )
    df_covid19_region = df_covid19_region.fillna(value=0)


    return df_covid19_region

#%%
df_covid19_region = get_data(URL_OPENCOVID19)
df_regions = pd.read_csv(url_pop_ccaa)
#print(df_covid19_es.head())
#print(df_covid19_region.head())
#print(df_regions)

#%% create necessary variables

# Change dates to correct format
# dates = pd.DataFrame(df_covid19_region['fecha'])
# df_Madrid = df_covid19_region[df_covid19_region["CCAA"].isin(["Madrid"])]
# dates = pd.to_datetime(df_Madrid.iloc[:,
#     df_covid19_region.columns.get_loc('fecha')],format="%Y/%m/%d")

# Parece que no puedo convertir la fecha a datetime porque tengo fechas repetidas. o eso entiendo
# pippo = pd.to_datetime(df_covid19_region["fecha"],format="%Y/%m/%d")
# add population information
df_covid19_region = df_covid19_region.merge(df_regions,on='CCAA',how='inner')
#col_idx = [1,2]+list(range(4,9))


col_idx = list(range(0,df_covid19_region.shape[1]))
df_covid19_es = df_covid19_region.iloc[:,col_idx].groupby(['fecha'],as_index=False).sum()
# create a new index based from day after 5 deaths
df_covid19_es["days_after_5_deaths"] = (
    df_covid19_es[df_covid19_es.muertes > 5]
    ["muertes"]
    .rank(method="first", ascending=True)
)
# create a new index based from day after 50 confirmed
df_covid19_es["days_after_50_confirmed"] = (
    df_covid19_es[df_covid19_es.casos > 50]
    ["casos"]
    .rank(method="first", ascending=True)
)
df_covid19_es['CCAA'] = 'Total_pais'
df_covid19_es = df_covid19_es.fillna(value=0)

df_covid19_region = df_covid19_region.append(df_covid19_es)

df_covid19_region["dead_ratio"] = df_covid19_region["muertes"]/df_covid19_region["Población"]*100000
df_covid19_region["cases_ratio"] = df_covid19_region["casos"]/df_covid19_region["Población"]*100000
df_covid19_region["new_cases_ratio"] = df_covid19_region["nuevos"]/df_covid19_region["Población"]*100000

df_covid19_region["fecha_D"] = pd.to_datetime(df_covid19_region["fecha"],format="%Y/%m/%d")

regions = list(df_covid19_region.CCAA.unique())
x_date_var = "fecha_D"


#%% Streamlit inputs %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
################################################################################################
viz_option = st.sidebar.selectbox("Visualisation: ", ("-","cumulative", "day delta"))

multiselection = st.sidebar.multiselect(
    "Choose the regions:", regions, default=regions
)


#%% get df_covid19_region based on region in multiselection
# unit_testing variables
# multiselection = regions
# viz_option = "graph"
# scale = "linear"

# code
df_covid19_region = df_covid19_region[
    df_covid19_region["CCAA"].isin(multiselection)
].sort_values(by=["CCAA", "fecha"], ascending=[True, False])

# intentar pintarlo awquí fuera
# comparar mis datos con los originales
# ver si el script original funciona en interactivo

# c_deaths = (
#     alt.Chart(df_covid19_es).
#     mark_line(point=True).
#     encode(
#             x="days_after_5_deaths",
#             y="muertes",
#         ).interactive()
# )

st.sidebar.info(
    "Thanks to Tlse Data Engineering for the [original project](https://github.com/TlseDataEngineering/data-app-covid19)."
)

text_4_regions = """👈 You can remove/add regions and graphs are updated automatically."""
if viz_option == "-":
    st.write("""👈 Select an analysis type from the dropdown menu on the left.""")

elif viz_option == "cumulative":
    st.write(text_4_regions)
    if st.checkbox("Relative x-axis"):
        x_var = ["days_after_50_confirmed","days_after_5_deaths"]
    else:
        x_var = [x_date_var,x_date_var]
    
    if st.checkbox("Numbers relative to population"):
        y_var = ["cases_ratio","dead_ratio"]
        st.info("""Values are relative to 100k people""")
    else:
        y_var = ["casos","muertes"]        
    
    if st.checkbox("Log Scale"):
        max_log_cases = [truncate_10(df_covid19_region[y_var[0]].max(),"up"),
         truncate_10(df_covid19_region[y_var[1]].max(),"up")]
        min_log_cases = (
            [truncate_10(
                df_covid19_region[df_covid19_region[y_var[0]]>0][y_var[0]].min(),"down"),
         truncate_10(
                df_covid19_region[df_covid19_region[y_var[1]]>0][y_var[1]].min(),"down")])
        scale_t = "log"
    else:
        scale = alt.Scale(type="linear")
        scale_t = "linear"        

    # make plot on nb of diagnosed by regions    
    if scale_t == "log":
        scale = alt.Scale(type="log", domain=[min_log_cases[0], max_log_cases[0]], clamp=True)
    
    single_nearest = alt.selection_single(on='mouseover', nearest=True,empty='none')
    Line_Base_Chart = (
        alt.Chart(df_covid19_region)
        .mark_line()
        .encode(
            color=alt.condition(
                single_nearest,
                alt.Color("CCAA:N", scale=alt.Scale(scheme="category20b")), 
                alt.value('lightgray'))
        ).add_selection(
        single_nearest
        ).interactive()
    )

    c_diagnosed = (
        Line_Base_Chart
        .encode(
            alt.X(x_var[0]),
            alt.Y(y_var[0], scale=scale),       
            tooltip=[x_var[0], y_var[0], "CCAA"],                    
    ))    
 
    # make plot on nb of deces by regions
    if scale_t == "log":
        scale = alt.Scale(type="log", domain=[min_log_cases[1], max_log_cases[1]], clamp=True)
    c_deaths = (
        Line_Base_Chart
        .encode(
            alt.X(x_var[1]),
            alt.Y(y_var[1], scale=scale),
            tooltip=[x_var[1], y_var[1], "CCAA"],
        )
    )
    
    if scale_t == "log":
        scale = alt.Scale(type="log", domain=[min_log_cases[0], max_log_cases[0]], clamp=True)
    
    st.altair_chart(c_diagnosed, use_container_width=True)
    st.altair_chart(c_deaths, use_container_width=True)
    st.write("""\n\n""")

    st.info("""Cumulated distributions of total cases, recovered and fatalities""")
    
    if st.checkbox("y axis independent for each region"):
        y_scale_rs = "independent"
    else:
        y_scale_rs = "shared"

    area_st_1 = (
    alt.Chart(df_covid19_region).mark_area(opacity=0.5,line=True)
    .encode(
        alt.Y('casos:Q',scale=scale),    
        x=x_var[0],
        color=alt.value('#1f77b4'),
    ).properties(
        height=150,
        width=180,
    ))
    area_st_2 = (
        alt.Chart(df_covid19_region).transform_fold(
        ['muertes', 'curados'],
    ).mark_area(line=True).encode(
            alt.Y('value:Q',stack=True,scale=scale),        
            #alt.Color('key:N', scale=alt.Scale(scheme='set1')),#color='key:N',scheme=['#de3907','#5cc481']
            color=alt.Color('key:N',
                    scale=alt.Scale(
                #domain='key',
                range=['#71f594','#e41a1c'])),#ff7f0e,#71f594
            x=x_var[0],
    ).properties(
        height=150,
        width=180,
    ))    
    
    c_area_st = alt.layer(    
    area_st_1,
    area_st_2,
    ).facet(    
        facet='CCAA:N',
        columns=3
    ).resolve_scale(y=y_scale_rs)     

    st.altair_chart(c_area_st, use_container_width=True)

elif viz_option=="day delta":
    st.write(text_4_regions)
    if st.checkbox("Relative x-axis"):
        x_var = ["days_after_50_confirmed","days_after_5_deaths"]
    else:
        x_var = [x_date_var,x_date_var]
    
    if st.checkbox("Numbers relative to population"):
        y_var = ["new_cases_ratio","dead_ratio"]
        st.info("""Values are relative to 100k people""")
    else:
        y_var = ["nuevos","muertes"]   
    c_heatmap_confirmed = (
        alt.Chart(df_covid19_region)
        .mark_rect()
        .encode(
            alt.X(x_var[0]),
            alt.Y("CCAA:N"),
            alt.Color(y_var[0]+":Q", scale=alt.Scale(scheme="yelloworangered")), #iridis
            tooltip=[x_var[0], "CCAA", y_var[0]],
        )
        .transform_filter((datum.nuevos >= 0))
        .interactive()
    )
    st.altair_chart(c_heatmap_confirmed, use_container_width=True)
    st.write("""\n\n""")
    if st.checkbox("y axis independent for each region"):
        y_scale_rs = "independent"
    else:
        y_scale_rs = "shared"
    c_histog_new = (
        alt.Chart(df_covid19_region)
        .mark_bar()#width)
        .encode(
            alt.X(x_var[0]+":T"),#type="temporal",timeUnit="day"),Esto funciona pero me pinta solo una semana
            alt.Y(y_var[0]+":Q"),            
            tooltip=[x_var[0], y_var[0]],
        )
        .properties(
            height=180,
            width=180,
            )
        .facet(
            facet='CCAA:N',
            columns=3,
        ).resolve_scale(y=y_scale_rs)
        .interactive()
    )
    
    
    st.altair_chart(c_histog_new, use_container_width=True)

    # st.info("""Aquí me gustaría probar los ridgelines. Quizás lo que más me guste es lollypop""")

elif viz_option=="histo":
    st.info("""En alguna parte podría pintar unas barras rellenas. Total de casos rellenos con el 
    porcentaje de curados, hospitalizados, UCI, muertos. O barras superpuestas unas sobre otras con
    transparencia""")

st.info(
    """ by: [R. Jimenez Sanchez](https://www.linkedin.com/in/robertojimenezsanchez/) | source: [GitHub](https://www.github.com)
        | data source: [victorvicpal/COVID19_es (GitHub)](https://raw.githubusercontent.com/victorvicpal/COVID19_es/master/data/final_data/dataCOVID19_es.csv). """
)


